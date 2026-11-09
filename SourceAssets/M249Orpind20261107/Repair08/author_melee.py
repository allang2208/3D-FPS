"""Preserve the installed grip, bake its existing handoff, solve a continuous V9 right arm."""
from pathlib import Path
import pickle,json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
r=Path(__file__).resolve().parent;root=r.parent
def mat(v):
    a=np.asarray(v);m=np.zeros((*a.shape[:-1],4,4));m[...,3,3]=1
    m[...,:3,:3]=R.from_quat(a[...,3:7].reshape(-1,4)).as_matrix().reshape(*a.shape[:-1],3,3)*a[...,None,7:10];m[...,:3,3]=a[...,:3];return m
def unit(v):return v/max(np.linalg.norm(v),1e-10)
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def swing(a,b):
    a,b=unit(a),unit(b);return R.from_quat(np.r_[np.cross(a,b),1+a@b]).as_matrix()
def frame(a,h):
    a=unit(a);h=unit(h-a*(a@h));return np.stack((a,np.cross(h,a),h),axis=1)
def turn(axis,angle):return R.from_rotvec(unit(axis)*angle).as_matrix()
def blend(a,b,t):return a@R.from_rotvec(R.from_matrix(a.T@b).as_rotvec()*t).as_matrix()
def ease(x):
    x=np.clip(x,0,1);return x*x*x*(10+x*(-15+6*x))
geo=pickle.load(open(root/'Repair06/geometry.pkl','rb'));names=geo['names'];parents={n:(names[p] if p>=0 else None) for n,p in zip(names,geo['parents'])}
B={n:mat(np.array(v)[None])[0] for n,v in zip(names,geo['bind'])}
src=pickle.load(open(r/'DATA_MODEL_quick_melee.pkl','rb'));idle=pickle.load(open(r/'DATA_MODEL_idle.pkl','rb'))
from scipy.spatial.transform import Slerp
frames=np.asarray(src['frames']);original_times=np.arange(len(frames))/src['fps'];fps=240;duration=src['duration']
times=np.linspace(0,original_times[-1],round(duration*fps)+1);dense=np.zeros((len(times),len(names),10))
for i,n in enumerate(names):
    dense[:,i,3:7]=Slerp(original_times,R.from_quat(frames[:,i,3:7]))(times).as_quat()
    for j in (0,1,2,7,8,9):dense[:,i,j]=np.interp(times,original_times,frames[:,i,j])
def world(row):
    out={}
    for i,n in enumerate(names):
        m=mat(row[i:i+1])[0];parent=parents[n];out[n]=out[parent]@m if parent else m
    return out
home=world(np.asarray(idle['frames'])[0]);W=[world(row) for row in dense]
active=ease(times/.065)*(1-ease((times-.65)/.25))
# Bake the previous entry/recovery into all tracks, then solve right-hand contact
# against that very same final gun transform. Runtime must not blend it twice.
for i,p in enumerate(W):
    a=min(np.clip(times[i]/.035,0,1),1-ease((times[i]/duration-.78)/.22))
    current={}
    for n in names:
        parent=parents[n];local=np.linalg.inv(p[parent])@p[n] if parent else p[n]
        base=np.linalg.inv(home[parent])@home[n] if parent else home[n]
        m=local.copy();m[:3,3]=base[:3,3]*(1-a)+local[:3,3]*a
        m[:3,:3]=blend(rot(base),rot(local),a)*(np.linalg.norm(base[:3,:3],axis=0)*(1-a)+np.linalg.norm(local[:3,:3],axis=0)*a)
        current[n]=current[parent]@m if parent else m
    W[i]=current
grip=np.linalg.inv(home['WPN_root'])@home['hand_r']
U0=B['lowerarm_r'][:3,3]-B['upperarm_r'][:3,3];F0=B['hand_r'][:3,3]-B['lowerarm_r'][:3,3]
H0=unit(np.cross(U0,F0));FU=frame(U0,H0);FF=frame(F0,H0)
S0,E0,H= [home[n][:3,3] for n in ('upperarm_r','lowerarm_r','hand_r')]
la,lb=np.linalg.norm(E0-S0),np.linalg.norm(H-E0)
minimum=np.sqrt(la*la+lb*lb+2*la*lb*np.cos(np.radians(135)))
maximum=(la+lb)*.965
write=['clavicle_r','upperarm_r','upperarm_twist_01_r','upperarm_twist_02_r','lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r','hand_r']
controls=[];rolls=[];previous=np.zeros(4);roll_reference=0.
def solve_pose(i,x,reference):
    p=W[i];hand=p['WPN_root']@grip;h=hand[:3,3]
    base=S0+(p['upperarm_r'][:3,3]-S0)*.12
    a=base+x[:3];axis=unit(h-a);distance=np.linalg.norm(h-a)
    length=np.clip(distance,minimum,maximum);a+=axis*(distance-length);distance=length
    pole=unit(E0-S0);pole=unit(pole-axis*(axis@pole));pole=turn(axis,x[3])@pole
    along=(la*la-lb*lb+distance*distance)/(2*distance)
    e=a+axis*along+pole*np.sqrt(max(0,la*la-along*along))
    u,f=e-a,h-e;hinge=unit(np.cross(u,f));bend=np.arccos(np.clip(unit(u)@unit(f),-1,1))
    crease=np.clip((np.degrees(bend)-30)/40,0,1);crease=crease*crease*(3-2*crease)
    neutral=turn(f,np.radians(-20)*crease)@frame(f,hinge)@FF.T
    palm=rot(hand)@rot(B['hand_r']).T
    distal=swing(palm@F0,f)@palm
    quat=R.from_matrix(distal@neutral.T).as_quat()
    roll=2*np.arctan2(quat[:3]@unit(f),quat[3]);roll+=2*np.pi*round((reference-roll)/(2*np.pi))
    return a,e,h,hand,palm,neutral,roll
for i in range(len(W)):
    if active[i]<1e-8:controls.append(np.zeros(4));rolls.append(0.);continue
    guess=previous.copy()
    def residual(x):
        a,e,h,hand,palm,neutral,roll=solve_pose(i,x,roll_reference)
        angle=np.arccos(np.clip(unit(h-e)@unit(palm@F0),-1,1))
        return np.r_[max(0,angle-np.radians(30))/np.radians(3),
            (a-S0)/np.array([13.,13.,10.]),(e-E0)/25.,
            (x-guess)/np.array([6.,6.,6.,.55]),x[3]/2.2,
            max(0,abs(roll)-np.radians(110))/np.radians(15),max(0,e[2]-h[2]+1)/3.,
            max(0,20.-a[1])/.12,max(0,a[2]-8.)/.3,max(0,2.-a[0])/.3]
    solved=least_squares(residual,guess,bounds=([-24,-24,-26,-2.6],[24,24,16,2.6]),max_nfev=70,ftol=2e-5,xtol=2e-5,gtol=2e-5)
    previous=solved.x;controls.append(previous.copy());roll_reference=solve_pose(i,previous,roll_reference)[-1];rolls.append(roll_reference)
controls=gaussian_filter1d(np.asarray(controls),1.5,axis=0,mode='nearest');rolls=np.unwrap(rolls)
result=[];metrics=[]
for i,x in enumerate(controls):
    p={n:m.copy() for n,m in W[i].items()};a,e,h,hand,palm,neutral,roll=solve_pose(i,x,rolls[i])
    f=h-e;u=e-a;fore_roll=np.clip(roll,-np.radians(110),np.radians(110))
    elbow=turn(f,roll-fore_roll)@neutral;upper=swing(elbow@U0,u)@elbow
    desired={n:p[n].copy() for n in write};desired['hand_r']=hand
    desired['clavicle_r'][:3,3]+=a-p['upperarm_r'][:3,3]
    for segment,origin,ref,restaxis,axis,driver in [('upperarm',a,B['upperarm_r'][:3,3],U0,u,upper),('lowerarm',e,B['lowerarm_r'][:3,3],F0,f,elbow)]:
        for suffix,share in [('',0),('_twist_01',1),('_twist_02',.5)]:
            n=segment+suffix+'_r';offset=B[n][:3,3]-ref;station=offset@restaxis/(restaxis@restaxis)
            d=turn(f,fore_roll*share)@driver if segment=='lowerarm' else driver
            desired[n][:3,3]=origin+station*axis+d@(offset-station*restaxis)
            desired[n][:3,:3]=d@rot(B[n])*np.linalg.norm(p[n][:3,:3],axis=0)
    for n in write:
        weight=active[i] if n!='hand_r' else 1.
        p[n][:3,3]=(1-weight)*p[n][:3,3]+weight*desired[n][:3,3]
        p[n][:3,:3]=blend(rot(p[n]),rot(desired[n]),weight)*np.linalg.norm(p[n][:3,:3],axis=0)
    # Preserve the exact idle finger curl after moving the right-hand parent.
    for n in names:
        if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky')):
            parent=parents[n];p[n]=p[parent]@np.linalg.inv(home[parent])@home[n]
    if i in (0,len(W)-1):p={n:m.copy() for n,m in home.items()}
    result.append(p)
    wristaxis=unit(rot(p['hand_r'])@rot(B['hand_r']).T@F0)
    metrics.append(np.degrees(np.arccos(np.clip(unit(p['hand_r'][:3,3]-p['lowerarm_r'][:3,3])@wristaxis,-1,1))))
authored=result
# The existing fast swing turns ~14 degrees in 1/240 s. Re-encode the final
# world-space grip densely so UE's independent local-chain interpolation cannot
# pull the palm off the handle between those keys.
export_fps=960;export_times=np.linspace(0,times[-1],round(duration*export_fps)+1)
dense_world={}
for n in names:
    m=np.array([p[n] for p in authored]);sc=np.linalg.norm(m[:,:3,:3],axis=1)
    q=R.from_matrix(m[:,:3,:3]/sc[:,None,:]);dst=np.tile(np.eye(4),(len(export_times),1,1))
    scale=np.stack([np.interp(export_times,times,sc[:,j]) for j in range(3)],axis=1)
    dst[:,:3,:3]=Slerp(times,q)(export_times).as_matrix()*scale[:,None,:]
    dst[:,:3,3]=np.stack([np.interp(export_times,times,m[:,j,3]) for j in range(3)],axis=1)
    dense_world[n]=dst
dense_world['hand_r']=dense_world['WPN_root']@grip
# Project the entry/recovery support onto the exact original two-bone lengths.
# World-space handoff blending must not shorten either arm segment.
for i in range(len(export_times)):
    a=dense_world['upperarm_r'][i,:3,3].copy();h=dense_world['hand_r'][i,:3,3].copy();old_e=dense_world['lowerarm_r'][i,:3,3].copy()
    axis=unit(h-a);distance=np.linalg.norm(h-a);along=(la*la-lb*lb+distance*distance)/(2*distance)
    center=a+axis*along;pole=unit(old_e-center-axis*((old_e-center)@axis));e=center+pole*np.sqrt(max(0.,la*la-along*along))
    for segment,origin,ref,restaxis,newaxis in [('upperarm',a,B['upperarm_r'][:3,3],U0,e-a),('lowerarm',e,B['lowerarm_r'][:3,3],F0,h-e)]:
        for suffix in ('','_twist_01','_twist_02'):
            n=segment+suffix+'_r';m=dense_world[n][i];d=rot(m)@rot(B[n]).T
            d=swing(d@restaxis,newaxis)@d;offset=B[n][:3,3]-ref;station=offset@restaxis/(restaxis@restaxis)
            m[:3,3]=origin+station*newaxis+d@(offset-station*restaxis)
            m[:3,:3]=d@rot(B[n])*np.linalg.norm(m[:3,:3],axis=0)
for n in names:
    if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky')):
        parent=parents[n];dense_world[n]=dense_world[parent]@np.linalg.inv(home[parent])@home[n]
tracks={}
for n in names:
    parent=parents[n];m=np.linalg.inv(dense_world[parent])@dense_world[n] if parent else dense_world[n]
    scales=np.linalg.norm(m[:,:3,:3],axis=1);qs=R.from_matrix(m[:,:3,:3]/scales[:,None,:]).as_quat()
    qs*=np.cumprod(np.r_[1,np.where((qs[1:]*qs[:-1]).sum(1)<0,-1,1)])[:,None]
    tracks[n]=np.c_[m[:,:3,3],qs,scales].round(9).tolist()
with gzip.open(root/'MotionInput/quick_melee.json.gz','rt') as f:source_asset=json.load(f)['source']
with gzip.open(r/'quick_melee.json.gz','wt') as f:json.dump(dict(source=source_asset,duration=duration,fps=export_fps,tracks=tracks),f,separators=(',',':'))
with (r/'candidate_world.pkl').open('wb') as f:pickle.dump(dict(names=names,fps=fps,duration=duration,frames=np.array([[np.r_[p[n][:3,3],R.from_matrix(rot(p[n])).as_quat(),np.linalg.norm(p[n][:3,:3],axis=0)] for n in names] for p in result])),f)
(r/'melee_authoring.json').write_text(json.dumps(dict(max_wrist_angle_deg=max(metrics),fps=fps,export_fps=export_fps,duration=duration,contact_seconds=1/6,controls=controls.tolist()),indent=2))
print('M249_MELEE_AUTHORED',len(result),'max wrist angle',max(metrics),flush=True)
