"""Fit the native grouped fore-end grasp to A762's wider body."""
import json,math,numpy as np,trimesh
from pathlib import Path
from scipy.spatial.transform import Rotation
from scipy.optimize import minimize
O=Path(__file__).parent;S=O.parent
data=json.loads((S/'RifleMagazineGrip20260922/fit_input.json').read_text())
src=json.loads((O/'support_input.json').read_text())
names=data['names'];parents=data['parents'];rest={n:np.array(m) for n,m in data['rest'].items()}
inv={n:np.linalg.inv(m) for n,m in rest.items()};local={n:inv[parents[n]]@rest[n] for n in names[1:]}
vertices=np.c_[np.array(data['vertices']),np.ones(len(data['vertices']))]
weights=np.array([[w.get(n,0) for n in names] for w in data['weights']]);weights/=weights.sum(1)[:,None]
bound={n:vertices@inv[n].T for n in names};labels=np.array(data['labels']);faces=np.array(data['faces'])
definition=(S/'RifleMagazineGrip20260922/IndexClearanceV4/author_index.py').read_text()
scope={}
exec('import numpy as np\nfrom scipy.spatial import ConvexHull\n'+definition[definition.index('class Shell:'):definition.index('def samples(')],scope)
body=src['body'];shell=scope['Shell']({'vertices':np.array(body['vertices'])[:,[0,2,1]].tolist(),'faces':body['faces']})
H=np.array(src['poses']['450']['hand_in_root']);H[1,3]+=.035
basis0={n:src['poses']['450']['basis'][n] for n in names[1:]}
def rot(q):return Rotation.from_quat([q[1],q[2],q[3],q[0]]).as_matrix()
def wxyz(m):
    q=Rotation.from_matrix(m).as_quat();return [float(q[3]),*map(float,q[:3])]
def pose(basis,hand):
    p={'hand_l':hand.copy()}
    for n in names[1:]:
        b=np.eye(4);b[:3,:3]=rot(basis[n]);p[n]=p[parents[n]]@local[n]@b
    skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
    return p,skin
p0,skin0=pose(basis0,H)
normals=trimesh.Trimesh(vertices=skin0,faces=faces,process=False).vertex_normals
palm=np.flatnonzero(np.array([n=='hand_l' or 'metacarpal' in n for n in labels])&(normals[:,2]>.5)&(skin0[:,1]<-.205))
digits=['index','middle','ring','pinky','thumb']
curl_axes={}
for digit in digits:
    a=p0[digit+'_02_l'][:3,1];b=p0[digit+'_03_l'][:3,1];axis=np.cross(a,b);axis/=np.linalg.norm(axis)
    curl_axes[digit]=p0[digit+'_03_l'][:3,:3].T@axis
def posed(x):
    basis=dict(basis0);hand=H.copy()
    turn=Rotation.from_euler('xyz',[x[7],x[8],x[14]],degrees=True).as_matrix();pivot=np.array([0.,-.24,.015])
    hand[:3,:3]=turn@hand[:3,:3];hand[:3,3]=pivot+turn@(hand[:3,3]-pivot)
    hand[0,3]+=x[0]/1000;hand[2,3]+=x[1]/1000
    for digit,angle in zip(digits,x[2:7]):
        n=digit+'_01_l'
        world=Rotation.from_rotvec(np.array([0,math.radians(angle),0])).as_matrix()@p0[n][:3,:3]
        basis[n]=wxyz(local[n][:3,:3].T@p0[parents[n]][:3,:3].T@world)
    for digit,angle in zip(digits,x[9:14]):
        n=digit+'_03_l';basis[n]=wxyz(rot(basis0[n])@Rotation.from_rotvec(curl_axes[digit]*math.radians(angle)).as_matrix())
    p,skin=pose(basis,hand);return basis,hand,p,skin
def points(skin):return np.concatenate([skin,skin[faces[::2]].mean(1)])
def clearance(x):return shell.clearance(points(posed(x)[3])[:,[0,2,1]])
def objective(x):
    skin=posed(x)[3];d=shell.clearance(skin[:,[0,2,1]])
    palm_patch=np.sort(d[palm])[:60]
    cost=4*(palm_patch.mean()-.6)**2+.025*np.sum(np.array(x[2:7])**2)+.02*(np.sum(np.array(x[7:9])**2)+x[14]**2)+.02*np.sum(np.array(x[9:14])**2)+.04*x[0]**2
    for digit in digits:
        patch=np.sort(d[np.array([n.startswith(digit+'_0') for n in labels])])[:20]
        cost+=.15*(patch.mean()-1)**2
    return cost
solved=minimize(objective,np.array([0.,4.,-12.,-6.,0.,0.,12.,0.,0.,-5.,-5.,0.,0.,-5.,0.]),method='SLSQP',
    bounds=[(-15,15),(-12,22),(-30,5),(-25,15),(-15,25),(-15,25),(-15,30),(-25,25),(-30,30)]+[(-25,10)]*5+[(-25,25)],
    constraints=[{'type':'ineq','fun':lambda x:clearance(x)-.35}],options={'maxiter':100,'ftol':.0001})
basis,hand,p,skin=posed(solved.x)
result={'hand_in_root':hand.tolist(),'finger_basis':basis,'skin_root':skin.tolist(),
    'parameters_mm_degrees':solved.x.tolist(),'success':bool(solved.success),'message':str(solved.message),
    'minimum_body_envelope_clearance_mm':float(clearance(solved.x).min()),
    'palm_patch_mean_mm':float(np.sort(shell.clearance(skin[palm][:,[0,2,1]]))[:60].mean()),
    'minimum_by_bone':{n:float(shell.clearance(skin[labels==n][:,[0,2,1]]).min()) for n in np.unique(labels)}}
(O/'fitted_support.json').write_text(json.dumps(result),encoding='utf-8')
print('A762_SUPPORT_FIT',{k:v for k,v in result.items() if k not in ('skin_root','finger_basis','hand_in_root')},flush=True)
