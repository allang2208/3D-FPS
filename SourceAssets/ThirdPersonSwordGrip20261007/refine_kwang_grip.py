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
def twist_angle(q,v):
    # Exact swing/twist projection in the principal angular branch.
    v=unit(v);t=2*math.atan2(np.dot(q[:3],v),q[3])
    t=(t+math.pi)%(2*math.pi)-math.pi
    return t

def distributed_twist(angle,fraction):
    # Polar blend of the two axial rotation frames. Unlike fraction*angle,
    # this is periodic: 0 and 360 produce the same helper pose, and crossing
    # +/-180 never switches a helper abruptly by 120 degrees. Jason's helpers
    # are at 1/3 and 2/3, away from the ambiguous half-weight opposing frames.
    return math.atan2(fraction*math.sin(angle),1-fraction+fraction*math.cos(angle))

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
    # Do not clamp signed atan2: crossing +/-pi otherwise jumps the elbow
    # from +105 to -105 degrees in one frame. Penalize deviation continuously.
    E=center+pole*radius
    bend=math.acos(np.clip(np.dot(unit(C-E),desired),-1,1))
    reach=max(0.,np.linalg.norm(C-A)-(l1+l2)*.975)
    return E,bend,swivel,reach

def arm_frames(w,side,hand,elbow=None):
    a,b,c=arms[side];A=w[a,:3];C=hand[:3]
    E=elbow if elbow is not None else elbow_solution(w,side,hand)[0]
    plane=unit(np.cross(E-A,C-E))
    rest_plane=unit(np.cross(bind[b,:3]-bind[a,:3],bind[c,:3]-bind[b,:3]))
    upper=mul(mul(basis(E-A,plane),inv(basis(bind[b,:3]-bind[a,:3],rest_plane))),bind[a,3:7])
    lower=mul(mul(basis(C-E,plane),inv(basis(bind[c,:3]-bind[b,:3],rest_plane))),bind[b,3:7])
    delta=mul(hand[3:7],inv(mul(lower,ref[c,3:7])))
    twist=twist_angle(delta,C-E)
    rest_upper=mul(w[parents[a],3:7],ref[a,3:7])
    neutral=mul(between(rot(rest_upper,unit(ref[b,:3])),E-A),rest_upper)
    upper_twist=twist_angle(mul(upper,inv(neutral)),E-A)
    return E,upper,lower,twist,upper_twist

def fit(f,w,side,hand,elbow=None):
    a,b,c=arms[side];E,upper,lower,twist,upper_twist=arm_frames(w,side,hand,elbow)
    set_q(f,a,upper);set_q(f,b,lower);set_q(f,c,hand[3:7])
    # Use a bounded physical twist, not an unwrapped number of full turns.
    # A 360-degree turn is identity on the wrist but becomes 120/240 degrees
    # on fractionally weighted helpers and would corrupt the return-to-idle.
    axis_local=unit(ref[c,:3])
    for suffix in ('01','02'):
        j=ix['lowerarm_twist_'+suffix+'_'+side]
        fraction=np.clip(np.dot(ref[j,:3],axis_local)/lengths[side][1],0,1)
        f[j,3:7]=mul(axis(axis_local,distributed_twist(twist,fraction)),ref[j,3:7])
    # Shoulder roll is likewise spread from clavicle to elbow. Do not inherit
    # a stale helper roll from a different skeleton's retargeted arm chain.
    for suffix in ('01','02'):
        j=ix['upperarm_twist_'+suffix+'_'+side]
        fraction=np.clip(np.dot(ref[j,:3],unit(ref[b,:3]))/lengths[side][0],0,1)
        f[j,3:7]=mul(axis(unit(ref[b,:3]),distributed_twist(-upper_twist,1-fraction)),ref[j,3:7])
    f[ix['upperarm_correctiveRoot_'+side],3:7]=mul(axis(unit(ref[b,:3]),-upper_twist),ref[ix['upperarm_correctiveRoot_'+side],3:7])
    f[ix['lowerarm_correctiveRoot_'+side],3:7]=ref[ix['lowerarm_correctiveRoot_'+side],3:7]

def refine(frames):
    poses=np.array(frames);world=[fk(f) for f in poses]
    weapons=[compose(w[ix['hand_r'],:7],hand_to_weapon) for w in world]
    # Plan a whole take, including its return to carry. Frame-by-frame angle
    # unwrapping can accumulate >360 degrees and the old exit envelope then
    # forces a complete reverse turn in eight frames.
    angles=np.radians(np.arange(-180.,181.,5.));zero=len(angles)//2
    delta=angles[:,None]-angles[None,:]
    roll_transition=.8*delta*delta
    roll_transition[np.abs(delta)>math.radians(20.01)]=np.inf
    rolls={}
    for side in arms:
        scores=[];elbows=[]
        a=arms[side][0];parent=parents[a]
        for w,wp in zip(world,weapons):
            row=[];points=[]
            for angle in angles:
                hand=target(wp,side,angle)
                E,bend,swivel,reach=elbow_solution(w,side,hand)
                row.append(bend*bend+8*max(0.,bend-math.radians(65))**2+
                           .12*(1-math.cos(swivel))+.025*reach*reach+.015*angle*angle)
                points.append(rot(inv(w[parent,3:7]),E-w[a,:3])/lengths[side][0])
            scores.append(row);elbows.append(points)
        scores=np.array(scores);elbows=np.array(elbows)
        costs=np.full(len(angles),np.inf);costs[zero]=scores[0,zero];links=[]
        for i in range(1,len(poses)):
            move=elbows[i,:,None,:]-elbows[i-1,None,:,:]
            candidates=costs[None,:]+roll_transition+18*np.sum(move*move,axis=2)
            previous=np.argmin(candidates,axis=1);links.append(previous)
            costs=scores[i]+candidates[np.arange(len(angles)),previous]
        path=[zero]
        for previous in reversed(links):path.append(int(previous[path[-1]]))
        values=angles[np.array(path[::-1])]
        values=savgol_filter(np.pad(values,(3,3),mode='edge'),7,2)[3:-3]
        values[:3]*=smooth(np.arange(3)/3);values[-3:]*=smooth(np.arange(2,-1,-1)/3)
        rolls[side]=values
    result=[]
    for i,(f,w,wp) in enumerate(zip(poses,world,weapons)):
        hands={s:target(wp,s,rolls[s][i]) for s in arms}
        shift=np.zeros(3)
        for _ in range(12):
            for s in arms:
                A=w[arms[s][0],:3];v=hands[s][:3]+shift-A;limit=sum(lengths[s])*.975
                if np.linalg.norm(v)>limit:shift-=unit(v)*(np.linalg.norm(v)-limit)
        for s in arms:hands[s][:3]+=shift
        for s in arms:fit(f,w,s,hands[s])
        result.append(f.tolist())
    # Smooth only skin-support bones, never the wrist contact or blade path.
    # Unwrap AFTER distribution: these are complete helper rotations, so an
    # integer winding still closes exactly at the ready pose.
    result=np.asarray(result)
    kernel=np.array([1,4,6,4,1],dtype=float)/16
    envelope=smooth(np.arange(len(result))/4)*smooth(np.arange(len(result)-1,-1,-1)/4)
    for s in arms:
        for prefix in ('upperarm_twist_01_','upperarm_twist_02_','lowerarm_twist_01_','lowerarm_twist_02_','upperarm_correctiveRoot_'):
            j=ix[prefix+s];direction=unit(ref[arms[s][1 if prefix.startswith('upper') else 2],:3])
            turn=np.unwrap([twist_angle(mul(q,inv(ref[j,3:7])),direction) for q in result[:,j,3:7]])
            filtered=np.convolve(np.pad(turn,(2,2),mode='edge'),kernel,mode='valid')
            turn+=(filtered-turn)*envelope
            result[:,j,3:7]=[mul(axis(direction,t),ref[j,3:7]) for t in turn]
    return result.tolist(),np.degrees(rolls['r']).tolist()

def densify_contact(frames,rolls):
    """Bake midpoint contact; independent bone interpolation opens a two-hand grip."""
    frames=np.asarray(frames);output=[];curves=[]
    for i in range(len(frames)-1):
        output.append(frames[i].tolist());curves.append(rolls[i])
        a,b=frames[i],frames[i+1];mid=(a+b)*.5
        q=b[:,3:7]*np.where(np.sum(a[:,3:7]*b[:,3:7],axis=1)<0,-1.,1.)[:,None]+a[:,3:7]
        mid[:,3:7]=q/np.linalg.norm(q,axis=1)[:,None]
        roll=(rolls[i]+rolls[i+1])*.5;w=fk(mid)
        weapon=compose(compose(w[ix['hand_r'],:7],hand_to_weapon),np.r_[0.,0.,0.,axis([0,0,1],-math.radians(roll))])
        relative=compose(compose(inverse(weapon),w[ix['hand_l'],:7]),inverse(grips['l']))
        left_roll=twist_angle(relative[3:7],[0,0,1])
        hands={'r':w[ix['hand_r'],:7].copy(),'l':target(weapon,'l',left_roll)}
        shift=np.zeros(3)
        for _ in range(12):
            for s in arms:
                v=hands[s][:3]+shift-w[arms[s][0],:3];limit=sum(lengths[s])*.975
                if np.linalg.norm(v)>limit:shift-=unit(v)*(np.linalg.norm(v)-limit)
        for s in arms:
            a,b,c=arms[s];A=w[a,:3];C=hands[s][:3]+shift;l1,l2=lengths[s]
            ray=unit(C-A);distance=np.linalg.norm(C-A)
            along=(l1*l1-l2*l2+distance*distance)/(2*distance)
            pole=w[b,:3]-A;pole=unit(pole-ray*np.dot(pole,ray))
            E=A+ray*along+pole*math.sqrt(max(0.,l1*l1-along*along))
            set_q(mid,a,mul(between(w[b,:3]-A,E-A),w[a,3:7]))
            set_q(mid,b,mul(between(w[c,:3]-w[b,:3],C-E),w[b,3:7]))
            set_q(mid,c,hands[s][3:7])
        output.append(mid.tolist());curves.append(roll)
    output.append(frames[-1].tolist());curves.append(rolls[-1])
    return output,curves

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
for label,original_clip in list(clips.items()):
    c=dict(original_clip)
    c['frames'],curve=densify_contact(c['frames'],c['curves']['SwordGripRoll'])
    c['curves']={'SwordGripRoll':curve};c['rate']*=2;clips[label]=c
result=dict(accepted);result['clips']=clips
result['provenance']+='; 20261007 review2: bounded shaft grip path, continuous elbow pole, periodic distributed twist helpers'
(OUT/'adapted-actions.json').write_text(json.dumps(result,separators=(',',':')))
print('KWANG_GRIP_READY '+str(len(clips)))
