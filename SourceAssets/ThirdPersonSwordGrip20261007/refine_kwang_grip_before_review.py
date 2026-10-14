"""Refine only the arms on the accepted Kwang body/weapon performance.

Hands may turn around the round grip; the sword keeps its accepted frame via
the matching SwordGripRoll attachment curve. Forearm twist uses Jason's actual
helper locations rather than concentrating pronation in the elbow/main bone.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize_scalar
from scipy.signal import savgol_filter

OUT=Path(__file__).resolve().parent
BASE=OUT.parent/'ThirdPersonSwordKwang20261006'
d=json.loads((BASE/'retargeted-poses.json').read_text())
accepted=json.loads((BASE/'adapted-actions.json').read_text())
equipment=json.loads((OUT.parent/'ThirdPersonSwordActions20261006/authoring-input.json').read_text())['equipment']
names,parents=d['names'],d['parents'];ix={n:i for i,n in enumerate(names)}
ref=np.array(d['reference'])
active=set()
for n in names:
    if any(k in n for k in ('upperarm','lowerarm','hand_','index_01','middle_01','pinky_01')):
        i=ix[n]
        while i>=0:active.add(i);i=parents[i]
active=sorted(active)

def unit(v):return np.asarray(v)/max(np.linalg.norm(v),1e-9)
def rot(q,v):return R.from_quat(q).apply(v)
def mul(a,b):return (R.from_quat(a)*R.from_quat(b)).as_quat()
def inv(q):return R.from_quat(q).inv().as_quat()
def axis(v,t):return R.from_rotvec(unit(v)*t).as_quat()
def compose(a,b):return np.r_[a[:3]+rot(a[3:7],b[:3]),mul(a[3:7],b[3:7])]
def inverse(t):return np.r_[rot(inv(t[3:7]),-t[:3]),inv(t[3:7])]
def basis(x,y):
    x=unit(x);y=unit(y-x*np.dot(y,x))
    return R.from_matrix(np.column_stack((x,y,np.cross(x,y)))).as_quat()
def fk(f):
    w=f.copy()
    for i in active:
        p=parents[i]
        if p>=0:
            w[i,:3]=w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
            w[i,3:7]=mul(w[p,3:7],f[i,3:7]);w[i,7:]=w[p,7:]*f[i,7:]
    return w
bind=fk(ref)
def set_q(f,b,q):
    w=fk(f);p=parents[b];f[b,3:7]=mul(inv(w[p,3:7]),q) if p>=0 else q
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def between(a,b):
    a,b=unit(a),unit(b);q=np.r_[np.cross(a,b),1+np.clip(np.dot(a,b),-1,1)]
    if np.linalg.norm(q)<1e-7:return axis(np.cross(a,[0,0,1]),math.pi)
    return q/np.linalg.norm(q)
def twist_angle(q,v,previous=None):
    # Exact swing/twist projection, unwrapped across the take.
    v=unit(v);t=2*math.atan2(np.dot(q[:3],v),q[3])
    t=(t+math.pi)%(2*math.pi)-math.pi
    if previous is not None:t=previous+(t-previous+math.pi)%(2*math.pi)-math.pi
    return t

def mount(side):
    pts=[]
    for sk in (equipment['reference'],{n:bind[i] for i,n in enumerate(names)}):
        h=np.array(sk['hand_'+side])
        pts.append(np.array([rot(inv(h[3:7]),np.array(sk[k+'_01_'+side])[:3]-h[:3]) for k in ('index','middle','pinky')]))
    a,b=pts;q=mul(basis(b[1],b[0]-b[2]),inv(basis(a[1],a[0]-a[2])))
    return np.r_[b.mean(0)-rot(q,a.mean(0)),q]
native=equipment['pose']
grips={s:compose(inverse(np.array(native['WPN_root'])[:7]),compose(np.array(native['hand_'+s])[:7],inverse(mount(s)))) for s in ('r','l')}
hand_to_weapon=inverse(grips['r'])
arms={s:[ix[k+'_'+s] for k in ('upperarm','lowerarm','hand')] for s in ('r','l')}
lengths={s:[np.linalg.norm(ref[arms[s][k],:3]) for k in (1,2)] for s in arms}

def target(weapon,side,roll):
    # Roll around the shaft, retaining grip height, radial contact and fingers.
    return compose(weapon,compose(np.r_[0.,0.,0.,axis([0,0,1],roll)],grips[side]))

def elbow_solution(w,side,hand):
    a,b,c=arms[side];A=w[a,:3];C=hand[:3];l1,l2=lengths[side]
    ray=unit(C-A);distance=np.clip(np.linalg.norm(C-A),abs(l1-l2)+.001,(l1+l2)*.985)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    center=A+ray*along;radius=math.sqrt(max(.0001,l1*l1-along*along))
    old=w[b,:3]-center;old=unit(old-ray*np.dot(old,ray))
    desired=rot(hand[3:7],rot(inv(ref[c,3:7]),unit(ref[c,:3])))
    # Minimize wrist swing with a donor elbow-plane preference. Axial grip
    # roll and elbow swivel are independent, not a single forearm rotation.
    pole=unit(old*.16-(desired-ray*np.dot(desired,ray))*radius/l2)
    swivel=math.atan2(np.dot(ray,np.cross(old,pole)),np.dot(old,pole))
    swivel=np.clip(swivel,-math.radians(105),math.radians(105))
    E=center+rot(axis(ray,swivel),old)*radius
    bend=math.acos(np.clip(np.dot(unit(C-E),desired),-1,1))
    reach=max(0.,np.linalg.norm(C-A)-(l1+l2)*.975)
    return E,bend,swivel,reach

def fit(f,w,side,hand,history):
    a,b,c=arms[side];A=w[a,:3];C=hand[:3];E,_,_,_=elbow_solution(w,side,hand)
    plane=unit(np.cross(E-A,C-E))
    rest_plane=unit(np.cross(bind[b,:3]-bind[a,:3],bind[c,:3]-bind[b,:3]))
    upper=mul(mul(basis(E-A,plane),inv(basis(bind[b,:3]-bind[a,:3],rest_plane))),bind[a,3:7])
    lower=mul(mul(basis(C-E,plane),inv(basis(bind[c,:3]-bind[b,:3],rest_plane))),bind[b,3:7])
    set_q(f,a,upper);set_q(f,b,lower);set_q(f,c,hand[3:7])
    # Main forearm stays on the elbow hinge. Skin helpers progressively carry
    # pronation, while the hand retains the exact shaft contact orientation.
    delta=mul(hand[3:7],inv(mul(lower,ref[c,3:7])))
    twist=twist_angle(delta,C-E,history.get(side));history[side]=twist
    axis_local=unit(ref[c,:3])
    for suffix in ('01','02'):
        j=ix['lowerarm_twist_'+suffix+'_'+side]
        fraction=np.clip(np.dot(ref[j,:3],axis_local)/lengths[side][1],0,1)
        f[j,3:7]=mul(axis(axis_local,twist*fraction),ref[j,3:7])
    # Shoulder roll is likewise spread from clavicle to elbow. Do not inherit
    # a stale helper roll from a different skeleton's retargeted arm chain.
    p=parents[a];w_now=fk(f);rest_upper=mul(w_now[p,3:7],ref[a,3:7])
    neutral=mul(between(rot(rest_upper,unit(ref[b,:3])),E-A),rest_upper)
    upper_twist=twist_angle(mul(upper,inv(neutral)),E-A,history.get(side+'u'));history[side+'u']=upper_twist
    for suffix in ('01','02'):
        j=ix['upperarm_twist_'+suffix+'_'+side]
        fraction=np.clip(np.dot(ref[j,:3],unit(ref[b,:3]))/lengths[side][0],0,1)
        f[j,3:7]=mul(axis(unit(ref[b,:3]),-upper_twist*(1-fraction)),ref[j,3:7])
    f[ix['upperarm_correctiveRoot_'+side],3:7]=mul(axis(unit(ref[b,:3]),-upper_twist),ref[ix['upperarm_correctiveRoot_'+side],3:7])
    f[ix['lowerarm_correctiveRoot_'+side],3:7]=ref[ix['lowerarm_correctiveRoot_'+side],3:7]

def refine(frames):
    poses=np.array(frames);world=[fk(f) for f in poses]
    weapons=[compose(w[ix['hand_r'],:7],hand_to_weapon) for w in world]
    rolls={s:[] for s in arms};previous={s:0. for s in arms}
    for i,(w,wp) in enumerate(zip(world,weapons)):
        for side in arms:
            prior=previous[side]
            def cost(angle):
                _,bend,swivel,reach=elbow_solution(w,side,target(wp,side,angle))
                return bend*bend+swivel*swivel*.06+((angle-prior)*.10)**2+reach*reach*.025
            choices=np.linspace(prior-math.pi,prior+math.pi,25)
            best=min(choices,key=cost)
            opt=minimize_scalar(cost,bounds=(best-math.pi/12,best+math.pi/12),method='bounded',options={'xatol':.002})
            previous[side]=opt.x;rolls[side].append(opt.x)
    for side in arms:
        rolls[side]=savgol_filter(rolls[side],min(9,(len(poses)-1)//2*2+1),2)
        # Return to the accepted ordinary carry without a grip/mount pop.
        for i in range(len(poses)):
            rolls[side][i]*=smooth(i/8)*smooth((len(poses)-1-i)/8)
    history={};result=[]
    for i,(f,w,wp) in enumerate(zip(poses,world,weapons)):
        hands={s:target(wp,s,rolls[s][i]) for s in arms}
        # Translate the entire pair together when either wrist exceeds reach;
        # never clamp the two wrists independently and tear open the grip.
        shift=np.zeros(3)
        for _ in range(12):
            for s in arms:
                A=w[arms[s][0],:3];v=hands[s][:3]+shift-A;limit=sum(lengths[s])*.975
                if np.linalg.norm(v)>limit:shift-=unit(v)*(np.linalg.norm(v)-limit)
        for s in arms:hands[s][:3]+=shift
        for s in arms:fit(f,w,s,hands[s],history)
        result.append(f.tolist())
    return result,np.degrees(rolls['r']).tolist()

clips={}
for label in ('Uppercut','Overhead'):
    c=dict(accepted['clips'][label]);c['frames'],roll=refine(c['frames'])
    c['curves']={'SwordGripRoll':roll};clips[label]=c
    print('KWANG_GRIP_AUTHORED '+label,flush=True)
clips['DashOverhead']=clips['Overhead']
phases=['Whirlwind.Start','Whirlwind.Loop','Whirlwind.End']
merged=[];spans={}
for label in phases:
    frames=accepted['clips'][label]['frames'];start=max(0,len(merged)-1)
    merged.extend(frames if not merged else frames[1:]);spans[label]=(start,len(merged))
refined,roll=refine(merged)
for label in phases:
    c=dict(accepted['clips'][label]);start,end=spans[label]
    c['frames']=refined[start:end];c['curves']={'SwordGripRoll':roll[start:end]};clips[label]=c
result=dict(accepted);result['clips']=clips
result['provenance']+='; 20261007 anatomically fitted shaft grip, continuous elbow swivel and distributed twist helpers'
(OUT/'adapted-actions.json').write_text(json.dumps(result,separators=(',',':')))
print('KWANG_GRIP_READY '+str(len(clips)))
