"""Fit the complete donor hook to the real receiver envelope and bolt tab."""
import json,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;S=O.parent
data=json.loads((O/'geometry.json').read_text())['skin'];refs=json.loads((O/'reference_poses.json').read_text());donor=refs['ASH12']['samples']['140.4']
names=data['names'];parents=data['parents'];rest={n:np.array(m) for n,m in data['rest'].items()};inverse={n:np.linalg.inv(m) for n,m in rest.items()}
local={n:inverse[parents[n]]@rest[n] for n in names[1:]}
H=np.array(donor['bones']['hand_r']);pivot=np.array([-.0358,-.1694,.075]);H[:3,3]+=pivot-np.array(donor['bones']['index_03_r'])[:3,3]
Q=Rotation.from_euler('y',115,degrees=True).as_matrix();H[:3,:3]=Q@H[:3,:3];H[:3,3]=pivot+Q@(H[:3,3]-pivot)
p={'hand_r':H};remaining=names[1:]
while remaining:
    for n in list(remaining):
        if parents[n] not in p:continue
        q=donor['basis'][n];b=np.eye(4);b[:3,:3]=Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
        p[n]=p[parents[n]]@local[n]@b;remaining.remove(n)
v=np.c_[data['vertices'],np.ones(len(data['vertices']))];weights=np.array([[w.get(n,0) for n in names] for w in data['weights']]);weights/=weights.sum(1)[:,None]
skin=sum((v@inverse[n].T@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
actual=json.loads((O/'contact_diagnosis.json').read_text())
if 'skin_vertices' in actual:
    exact=np.array(actual['skin_vertices'])
script=(S/'RifleMagazineGrip20260922/IndexClearanceV4/author_index.py').read_text();scope={}
exec('import numpy as np\nfrom scipy.spatial import ConvexHull\n'+script[script.index('class Shell:'):script.index('def samples(')],scope)
body=json.loads((S/'A762EmptySupport20260922/support_input.json').read_text())['body']
shell=scope['Shell']({'vertices':np.array(body['vertices'])[:,[0,2,1]].tolist(),'faces':body['faces']})
faces=np.array(data['faces']);points=np.concatenate([skin,skin[faces].mean(1)])
rows=[]
for dx in (0,-.003,-.005,-.007,-.009,-.011,-.013,-.015,-.017):
    vv=points+np.array([dx,0,0]);clearance=shell.clearance(vv[:,[0,2,1]])
    rows.append({'dx':dx,'minimum_clearance_mm':float(clearance.min()),'penetrating_samples':int(sum(clearance<0))})
print(rows,flush=True)
print('BODY_BOUNDS',np.min(body['vertices'],axis=0),np.max(body['vertices'],axis=0),flush=True)
d=shell.clearance(skin[:,[0,2,1]]);j=np.argmin(d)
print('DEEPEST',skin[j],data['weights'][j],d[j],flush=True)
(O/'body_clearance_fit.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

from scipy.optimize import minimize
target=np.array([-.0273,-.1654,.069]);pivot=np.array([-.0358,-.1694,.075])
index=np.array([i for i,w in enumerate(data['weights']) if sum(value for name,value in w.items() if name.startswith('index_0'))>.6])
states=[]
for frame in ('310','320','340'):
    pp={n:np.array(m) for n,m in refs['A762']['samples'][frame]['bones'].items()}
    A=pp['upperarm_r'][:3,3];E0=pp['lowerarm_r'][:3,3];l1=np.linalg.norm(E0-A);l2=np.linalg.norm(pp['hand_r'][:3,3]-E0)
    pull=pp['WPN_bolt'][:3,3]-np.array(refs['A762']['samples']['310']['bones']['WPN_bolt'])[:3,3]
    states.append((A,l1,l2,pull))
rest_axis=rest['hand_r'][:3,3]-rest['lowerarm_r'][:3,3];rest_axis/=np.linalg.norm(rest_axis)
def transform(x):
    q=Rotation.from_euler('xyz',x[3:],degrees=True).as_matrix();translation=np.array(x[:3])/1000
    return q,translation
def posed(x):
    q,t=transform(x);return (points-pivot)@q.T+pivot+t
def bends(x):
    q,t=transform(x);hh=H.copy();hh[:3,:3]=q@H[:3,:3];hh[:3,3]=q@(H[:3,3]-pivot)+pivot+t
    heading=hh[:3,:3]@rest['hand_r'][:3,:3].T@rest_axis;out=[]
    for A,l1,l2,pull in states:
        T=hh[:3,3]+pull;dist=np.linalg.norm(T-A);axis=(T-A)/dist;along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        pole=T-heading*l2-A;pole-=axis*np.dot(pole,axis);pole/=np.linalg.norm(pole)
        E=A+axis*along+pole*np.sqrt(max(0,l1*l1-along*along));actual=(T-E)/np.linalg.norm(T-E)
        out.append(np.degrees(np.arccos(np.clip(np.dot(actual,heading),-1,1))))
    return np.array(out)
def objective(x):
    v=posed(x)[:len(skin)];patch=np.sort(np.linalg.norm(v[index]-target,axis=1)*1000)[:6]
    return 20*np.mean((patch-.8)**2)+.06*np.sum(np.maximum(bends(x)-24,0)**2)+.004*np.sum(np.array(x[3:])**2)+.001*np.sum(np.array(x[:3])**2)
def constraint(x):
    v=posed(x)
    # Moving bolt includes a cover strip behind the tab. Keep the hook outside
    # its small envelope as well as outside the stationary receiver.
    center=np.array([-.0209,-.1107,.0641]);half=np.array([.0059,.0949,.0139])
    delta=np.abs(v-center)-half
    bolt=(np.linalg.norm(np.maximum(delta,0),axis=1)+np.minimum(np.max(delta,axis=1),0))*1000-.6
    return np.concatenate([bolt]+[shell.clearance((v+np.array([0,pull,0]))[:,[0,2,1]])-.6 for pull in (0,.0373,.0746)])
initial=json.loads((O/'fitted_contact.json').read_text())['parameters_mm_degrees'] if (O/'fitted_contact.json').exists() else [-25,0,2,0,-8,-25]
solution=minimize(objective,initial,method='SLSQP',bounds=[(-65,25),(-35,35),(-30,40),(-110,110),(-100,65),(-175,120)],
    constraints=[{'type':'ineq','fun':constraint}],options={'maxiter':100,'ftol':.0005})
q,t=transform(solution.x);hand=H.copy();hand[:3,:3]=q@H[:3,:3];hand[:3,3]=q@(H[:3,3]-pivot)+pivot+t
output={'success':bool(solution.success),'message':str(solution.message),'parameters_mm_degrees':solution.x.tolist(),
        'hand_in_root':hand.tolist(),'minimum_body_envelope_clearance_mm':float(constraint(solution.x).min()+.6),
        'estimated_wrist_bend_degrees':bends(solution.x).tolist(),'cost':float(solution.fun),
        'scope':'Native donor skin and receiver envelope, three points on the unchanged 74.6 mm pull. Not a game test.'}
(O/'fitted_contact.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print('CONTACT_FIT',output,flush=True)
