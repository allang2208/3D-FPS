"""SUPER90 R9 motion, M870 contacts, articulated arms and native twist stations.

Authoring only: no engine launch, render or gameplay test. Work in camera-space
centimetres so the current M870 hip framing remains the exact return target.
"""
import copy, gzip, json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R, Slerp

O=Path(__file__).parent
with gzip.open(O/'inputs.json.gz','rt',encoding='utf-8') as f:D=json.load(f)
T=D['weapons']['m870']; S=D['weapons']['super90']; fps=D['fps']
for spec in (T,S):
    spec['parents']={n:p if p in spec['names'] else None for n,p in spec['parents'].items()}
times=np.array(S['melee']['times']); frames=len(times)-1; duration=float(times[-1])
names=T['names']; parents=T['parents']; I=np.eye(4)
if abs(T['melee']['duration']-duration)>1e-5:raise RuntimeError('Preserve the existing M870 melee clock')

def unit(x):return x/max(np.linalg.norm(x),1e-10)
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def mat(v):
    m=I.copy();m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*v[7:10];m[:3,3]=v[:3];return m
def pack(m):return np.r_[m[:3,3],R.from_matrix(rot(m)).as_quat(),np.linalg.norm(m[:3,:3],axis=0)]
def world(local,ps):
    result={}
    def add(n):
        if n not in result:result[n]=(add(ps[n]) if ps[n] else I)@mat(local[n])
        return result[n]
    for n in local:add(n)
    return result
def ease(x):
    x=np.clip(x,0.,1.);return x*x*x*(10+x*(-15+6*x))
def turn(axis,angle):return R.from_rotvec(unit(axis)*angle).as_matrix()
def swing(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b)
    return np.eye(3) if np.linalg.norm(v)<1e-9 else turn(v,np.arctan2(np.linalg.norm(v),np.clip(a@b,-1,1)))
def blend(a,b,w):return Slerp([0,1],R.from_matrix([a,b]))([float(w)]).as_matrix()[0]
def frame(axis,normal):
    x=unit(axis);z=unit(normal-x*(normal@x));return np.column_stack((x,np.cross(z,x),z))
def beneath(n,root):
    while n:
        if n==root:return True
        n=parents[n]
    return False
def layer_values(track,ts):
    values=np.array(track['values']).reshape(-1,10);knots=np.array(track['times'])
    if len(values)==1:return np.tile(values,(len(ts),1))
    output=np.array([np.interp(ts,knots,values[:,j]) for j in range(10)]).T
    output[:,3:7]=Slerp(knots,R.from_quat(values[:,3:7]))(np.clip(ts,knots[0],knots[-1])).as_quat()
    return output
def decode(spec,role,family):
    clip=spec[role];rows=copy.deepcopy(clip['rows'])
    if family!='base':
        entry=next(c for c in spec['profiles'][family]['clips'] if c['base']==clip['path'])
        if entry['retained']:raise RuntimeError('Retained clip needs its own authoring input: '+family+' '+role)
        for track in entry['tracks']:
            for row,d in zip(rows,layer_values(track,np.array(clip['times']))):
                v=np.array(row[track['bone']]);v[:3]+=d[:3]
                v[3:7]=(R.from_quat(d[3:7])*R.from_quat(v[3:7])).as_quat();v[7:]+=d[7:]
                row[track['bone']]=v.tolist()
    return [world(row,spec['parents']) for row in rows]

# The same ruler and saved offsets as RifleHipFraming. SOURCE poses are kept
# separate from the prior compressed input record; only the M4 ruler is reused.
cal=json.loads((O.parent/'M870HipFraming20261017/calibration_inputs.json').read_text())
m4={n:mat([*v['p'],*v['q_xyzw'],1,1,1]) for n,v in cal['clips']['m4']['bones'].items()}
def axis_frame(p,up):
    return frame(p['WPN_FrontSight'][:3,3]-p['WPN_RearSight'][:3,3],rot(p['WPN_root'])@up)
yaw=R.from_euler('z',90,degrees=True).as_matrix()
target_axis=yaw@axis_frame(m4,np.array([0,0,1]))
reference_hand=np.array([0.,7.,-7.])+yaw@m4['hand_r'][:3,3]
offsets={'super90':np.array([6.,0,0]),'m870':np.array([-1.900510,1.680418,9.498009])}
def camera(spec,key):
    idle=decode(spec,'idle','base')[0];m=I.copy()
    m[:3,:3]=target_axis@axis_frame(idle,np.array([0,-1,0])).T
    m[:3,3]=reference_hand+offsets[key]-m[:3,:3]@idle['hand_r'][:3,3]
    return m
TC,SC=camera(T,'m870'),camera(S,'super90');TCi=np.linalg.inv(TC)
support=ease(times/.095)*(1-ease((times-.64)/.26))
fingers={side:[n for n in names if beneath(n,'hand_'+side)] for side in ('l','r')}
weapon=[n for n in names if beneath(n,'WPN_root')]

def arm_positions(idle,donor,source0,held,side,parameters):
    un,ln,hn=['%s_%s'%(n,side) for n in ('upperarm','lowerarm','hand')]
    a0,e0,h0=[idle[n][:3,3] for n in (un,ln,hn)]
    a_ref=a0+donor[un][:3,3]-source0[un][:3,3]
    e_ref=e0+donor[ln][:3,3]-source0[ln][:3,3]
    h=held[hn][:3,3];la,lb=np.linalg.norm(e0-a0),np.linalg.norm(h0-e0)
    a=a_ref+parameters[:3];axis=unit(h-a);reach=np.linalg.norm(h-a)
    reach_limit=.965*(la+lb)
    if reach>reach_limit:a+=axis*(reach-reach_limit);reach=reach_limit
    minimum=abs(la-lb)+.01
    if reach<minimum:a-=axis*(minimum-reach);reach=minimum
    pole=e_ref-a;pole=unit(pole-axis*(pole@axis))
    pole=turn(axis,parameters[3])@pole
    along=(la*la-lb*lb+reach*reach)/(2*reach)
    e=a+axis*along+pole*np.sqrt(max(0.,la*la-along*along))
    desired=rot(held[hn])@rot(idle[hn]).T@unit(h0-e0)
    return a,e,h,a_ref,e_ref,desired,reach/(la+lb)

def fit_support(idle,donors,held,side):
    # Fit sparse authoring controls, then interpolate them. The wrists are not
    # optimization variables: each stays locked to its own M870 idle contact.
    knots=list(range(0,len(times),4))
    if knots[-1]!=frames:knots.append(frames)
    fitted=[];previous=np.zeros(4)
    for i in knots:
        if support[i]<1e-8:fitted.append(np.zeros(4));previous=np.zeros(4);continue
        def residual(x):
            a,e,h,ar,er,desired,reach=arm_positions(idle,donors[i],donors[0],held[i],side,x)
            lateral=max(0.,min(a[1],h[1])-e[1]-2.) if side=='r' else max(0.,e[1]-max(a[1],h[1])-2.)
            return np.r_[(unit(h-e)-desired)/.22,(e-er)/9.,x[:3]/7.,x[3]/.85,
                         (x-previous)/np.array([12.,12.,12.,1.4]),
                         max(0.,e[2]-h[2]+1.)/3.,lateral/3.,max(0.,reach-.94)/.025]
        result=least_squares(residual,previous,bounds=([-13,-12,-12,-1.05],[13,12,12,1.05]),
                             max_nfev=40,ftol=1e-5,xtol=1e-5,gtol=1e-5)
        previous=result.x;fitted.append(previous.copy())
    return PchipInterpolator(times[knots],np.array(fitted),axis=0)(times)*support[:,None]

def solve_family(family):
    idle={n:TC@m for n,m in decode(T,'idle',family)[0].items()}
    donors=[{n:SC@m for n,m in p.items()} for p in decode(S,'melee',family)]
    inverse=np.linalg.inv(donors[0]['WPN_root']);held=[]
    for donor in donors:
        carry=donor['WPN_root']@inverse
        row={n:m.copy() for n,m in idle.items()}
        for n in set(weapon+fingers['l']+fingers['r']):row[n]=carry@idle[n]
        held.append(row)
    controls={side:fit_support(idle,donors,held,side) for side in ('l','r')}
    geometry={};rolls={}
    for side in ('l','r'):
        un,ln,hn=['%s_%s'%(n,side) for n in ('upperarm','lowerarm','hand')]
        u0=idle[ln][:3,3]-idle[un][:3,3];f0=idle[hn][:3,3]-idle[ln][:3,3];hinge0=np.cross(u0,f0)
        fu,ff=frame(u0,hinge0),frame(f0,hinge0);rows=[];rs=[]
        for i,row in enumerate(held):
            a,e,h,*_=arm_positions(idle,donors[i],donors[0],row,side,controls[side][i])
            upper,fore=e-a,h-e;hinge=np.cross(upper,fore)
            du=frame(upper,hinge)@fu.T;neutral=frame(fore,hinge)@ff.T
            palm=rot(row[hn])@rot(idle[hn]).T
            distal=swing(palm@f0,fore)@palm
            rs.append(R.from_matrix(distal@neutral.T).as_rotvec()@unit(fore))
            rows.append((a,e,h,fore,du,neutral))
        geometry[side]=rows;rolls[side]=np.unwrap(rs)
    result=[]
    for i,row in enumerate(held):
        for side in ('l','r'):
            un,ln,hn=['%s_%s'%(n,side) for n in ('upperarm','lowerarm','hand')]
            a,e,h,fore,du,neutral=geometry[side][i];roll=rolls[side][i]
            f0=idle[hn][:3,3]-idle[ln][:3,3]
            row['clavicle_'+side][:3,3]+=a-idle[un][:3,3]
            row[un][:3,3]=a;row[un][:3,:3]=du@idle[un][:3,:3]
            proximal=.35 if side=='r' else 0.
            prox=turn(fore,roll*proximal)@neutral
            for stem in ('lowerarm','lowerarm_aux','lowerarm_twist_02','lowerarm_twist_01'):
                n=stem+'_'+side;offset=idle[n][:3,3]-idle[ln][:3,3]
                station=offset@f0/(f0@f0)
                amount=proximal+(1-proximal)*ease(station/(2/3))
                driver=turn(fore,roll*amount)@neutral
                if stem=='lowerarm_aux':driver=blend(du,prox,.5) if side=='r' else prox
                row[n][:3,3]=e+station*fore+driver@(offset-station*f0)
                row[n][:3,:3]=driver@idle[n][:3,:3]
        if i in (0,frames):row={n:m.copy() for n,m in idle.items()}
        component={n:TCi@m for n,m in row.items()}
        result.append({n:pack(np.linalg.inv(component[parents[n]])@component[n] if parents[n] else component[n]) for n in names})
    return result,{side:controls[side].tolist() for side in controls}

def track(n,values,delta=False):
    v=np.array(values).copy()
    for i in range(1,len(v)):
        if v[i-1,3:7]@v[i,3:7]<0:v[i,3:7]*=-1
    constant=np.max(np.abs(v-v[0]))<1e-7
    return dict(bone=n,times=[0.] if constant else times.tolist(),values=v[0].tolist() if constant else v.ravel().tolist())

base,controls=solve_family('base')
output=dict(revision='M870QuickMelee-Super90R9-R1-20261017',melee_path=T['melee']['path'],duration=duration,
            fps=fps,frames=frames,base_tracks=[track(n,[row[n] for row in base]) for n in names],profiles={},
            ownership_curve=S['ownership_curve'],runtime_tested=False,visual_accepted=False)
all_controls={'base':controls};identity=np.array([0,0,0,0,0,0,1,0,0,0])
for family,spec in T['profiles'].items():
    rows,controls=solve_family(family);all_controls[family]=controls;tracks=[]
    for n in names:
        a=np.array([row[n] for row in base]);b=np.array([row[n] for row in rows])
        q=(R.from_quat(b[:,3:7])*R.from_quat(a[:,3:7]).inv()).as_quat();q[q[:,3]<0]*=-1
        delta=np.c_[b[:,:3]-a[:,:3],q,b[:,7:]-a[:,7:]]
        if np.max(np.abs(delta-identity))>1e-6:tracks.append(track(n,delta,True))
    output['profiles'][family]=dict(path=spec['path'],clip=dict(base=T['melee']['path'],duration=duration,tracks=tracks))
    print('M870_SUPER90_MELEE_AUTHORED',family,len(tracks),'sparse tracks',flush=True)
(O/'animation_patch.json').write_text(json.dumps(output,separators=(',',':')),encoding='utf-8')
(O/'authoring_controls.json').write_text(json.dumps(all_controls,separators=(',',':')),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps(dict(revision=output['revision'],duration=duration,contact_seconds=1/6,
    input_mode=D['source_mode'],reference=S['melee']['path'],target=T['melee']['path'],fps=fps,
    families=['base',*output['profiles']],method='SUPER90 weapon motion, M870 fixed contacts; shoulder/elbow articulation and R9 axial forearm stations',
    target_camera_matrix=TC.tolist(),reference_camera_matrix=SC.tolist(),
    authored_only=True,runtime_tested=False,visual_accepted=False),indent=2),encoding='utf-8')
print('M870_SUPER90_MELEE_READY',len(base),'samples',flush=True)
