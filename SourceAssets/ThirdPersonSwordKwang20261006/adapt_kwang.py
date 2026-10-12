"""Adapt Epic's complete body performances; only equipment and timing are fitted.

No replacement spine, pelvis, leg, footstep or right-hand attack path is authored.
Kwang's D take is a held-sword turning slash; Ability_R throws the sword and is
deliberately excluded. Gameplay owns whirlwind actor yaw and dash translation.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
d=json.loads((OUT/'retargeted-poses.json').read_text())
source=json.loads((OUT/'original-poses.json').read_text())
base=json.loads((OUT.parent/'ThirdPersonSwordActions20261006/authoring-input.json').read_text())
geometry=json.loads((OUT/'blade-geometry.json').read_text())
names,parents=d['names'],d['parents']
ix={n:i for i,n in enumerate(names)}
si={n:i for i,n in enumerate(source['names'])}
ref=np.array(d['reference'])

def unit(v):return np.asarray(v)/max(np.linalg.norm(v),1e-9)
def rot(q,v):return R.from_quat(q).apply(v)
def mul(a,b):return (R.from_quat(a)*R.from_quat(b)).as_quat()
def inv(q):return R.from_quat(q).inv().as_quat()
def axis(v,a):return R.from_rotvec(unit(v)*a).as_quat()
def compose(a,b):return np.r_[a[:3]+rot(a[3:7],b[:3]),mul(a[3:7],b[3:7])]
def inverse(t):return np.r_[rot(inv(t[3:7]),-t[:3]),inv(t[3:7])]
def frame_xy(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y))
    return R.from_matrix(np.column_stack((x,y,np.cross(x,y)))).as_quat()
def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p>=0:
            w[i,:3]=w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
            w[i,3:7]=mul(w[p,3:7],f[i,3:7]);w[i,7:]=w[p,7:]*f[i,7:]
    return w
def slerp(a,b,t):
    b=np.where(np.sum(a*b,axis=-1,keepdims=True)<0,-b,b)
    dot=np.clip(np.sum(a*b,axis=-1,keepdims=True),-1,1);th=np.arccos(dot);sn=np.sin(th)
    sn=np.where(sn<1e-7,1,sn)
    q=np.where(th<1e-6,a*(1-t)+b*t,(a*np.sin((1-t)*th)+b*np.sin(t*th))/sn)
    return q/np.linalg.norm(q,axis=-1,keepdims=True)
def blend(a,b,t):
    f=a*(1-t)+b*t;f[:,3:7]=slerp(a[:,3:7],b[:,3:7],t);return f
def smooth(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def sample(c,t):
    a=np.asarray(c['frames']);p=np.clip(t/c['duration']*(len(a)-1),0,len(a)-1)
    i=int(p);return blend(a[i],a[min(i+1,len(a)-1)],p-i)
def world_q(f,b,q):
    w=fk(f);p=parents[b];f[b,3:7]=mul(inv(w[p,3:7]),q) if p>=0 else q
def between(a,b):
    a=unit(a);b=unit(b);dot=np.clip(np.dot(a,b),-1,1)
    if dot<-.99999:
        v=np.cross(a,[1,0,0])
        if np.linalg.norm(v)<.01:v=np.cross(a,[0,1,0])
        return axis(v,math.pi)
    q=np.r_[np.cross(a,b),1+dot];return q/np.linalg.norm(q)

bind=fk(ref)
def mount(side):
    points=[]
    for skeleton in (base['equipment']['reference'],{n:bind[i] for i,n in enumerate(names)}):
        hand=np.array(skeleton['hand_'+side])
        points.append(np.array([rot(inv(hand[3:7]),np.array(skeleton[k+'_01_'+side])[:3]-hand[:3]) for k in ('index','middle','pinky')]))
    a,b=points;q=mul(frame_xy(b[1],b[0]-b[2]),inv(frame_xy(a[1],a[0]-a[2])))
    return np.r_[b.mean(0)-rot(q,a.mean(0)),q]
native=base['equipment']['pose']
grips={s:compose(inverse(np.array(native['WPN_root'])[:7]),compose(np.array(native['hand_'+s])[:7],inverse(mount(s)))) for s in ('r','l')}
hand_to_weapon=inverse(grips['r'])

# Kwang's source mesh supplies the actual long axis and blade face. Choose the
# edge facing the C take's cut. Current swords: length +Z, blade face XZ.
weapon_ref=np.array(source['reference'][si['weapon_r']])
vertices=rot(inv(weapon_ref[3:7]),np.array(geometry['vertices'])-weapon_ref[:3])
_,_,axes=np.linalg.svd(vertices-vertices.mean(0),full_matrices=False)
long=unit(axes[0])*np.sign(np.dot(axes[0],vertices.mean(0)))
normal=unit(axes[2]-long*np.dot(axes[2],long))
edge=np.cross(normal,long)
c=source['clips']['PrimaryAttack_C_Slow']
def source_tip(t):
    w=sample(c,t)[si['weapon_r']];return w[:3]+rot(w[3:7],long*110)
w=sample(c,.215)[si['weapon_r']]
v=rot(inv(w[3:7]),source_tip(.225)-source_tip(.205))
if np.dot(-edge,v)<0:normal=-normal;edge=-edge
blade_map=R.from_matrix(np.column_stack((edge,normal,long))).as_quat()

def fit_arm(f,side,target):
    """Keep donor elbow bend and upper-arm roll; fit only the held equipment."""
    a,b,c=[ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    w=fk(f);origin=w[a,:3];l1=np.linalg.norm(w[b,:3]-origin);l2=np.linalg.norm(w[c,:3]-w[b,:3])
    direction=unit(target[:3]-origin);distance=np.clip(np.linalg.norm(target[:3]-origin),abs(l1-l2)+.01,(l1+l2)*.98)
    endpoint=origin+direction*distance
    bend=w[b,:3]-origin;bend=unit(bend-direction*np.dot(bend,direction))
    if np.linalg.norm(bend)<.5:bend=unit(np.cross(direction,[0,0,1]))
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=origin+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
    world_q(f,a,mul(between(w[b,:3]-origin,elbow-origin),w[a,3:7]))
    w=fk(f);world_q(f,b,mul(between(w[c,:3]-w[b,:3],endpoint-w[b,:3]),w[b,3:7]))
    w=fk(f);neutral=mul(w[b,3:7],ref[c,3:7]);difference=mul(target[3:7],inv(neutral))
    if difference[3]<0:difference=-difference
    ray=unit(endpoint-elbow);twist=2*math.atan2(np.dot(difference[:3],ray),difference[3])
    world_q(f,b,mul(axis(ray,twist*.8),w[b,3:7]));world_q(f,c,target[3:7])
    # Twist helpers inherit the same forearm pronation as their driving segment.
    # Their local animation from UE's retarget remains otherwise untouched.

def rotate_body(f,q):
    # Keep root at its reference transform: runtime root locking must not strip
    # the heading correction baked into pelvis / other root children.
    for i,p in enumerate(parents):
        if p==0:
            f[i,:3]=rot(q,f[i,:3]);f[i,3:7]=mul(q,f[i,3:7])
    return f

def align_cut(label,contact):
    a=sample(source['clips'][label],contact)
    wp=a[si['weapon_r']];tip=wp[:3]+rot(wp[3:7],long*95)
    direction=(wp[:3]+tip)*.5-a[si['pelvis'],:3]
    return math.pi*.5-math.atan2(direction[1],direction[0])

spin_source=np.asarray(source['clips']['PrimaryAttack_D_Slow']['frames'])
source_ref=np.array(source['reference'])
q=(R.from_quat(spin_source[:,si['pelvis'],3:7])*R.from_quat(source_ref[si['pelvis'],3:7]).inv())
forward=q.apply([0,1,0]);spin_yaw=np.unwrap(np.arctan2(forward[:,1],forward[:,0]))

def pose(label,t,turn):
    f=sample(d['clips'][label],t);raw=sample(source['clips'][label],t)
    q=axis([0,0,1],turn);rotate_body(f,q)
    # Preserve full native body performance. Only a fixed-size sword grip is
    # fitted to the retargeted wrists; the right hand keeps its original arc.
    w=fk(f);wp_q=mul(q,mul(raw[si['weapon_r'],3:7],blade_map))
    right=np.r_[w[ix['hand_r'],:3],mul(wp_q,grips['r'][3:7])]
    fit_arm(f,'r',right)
    w=fk(f);weapon=compose(w[ix['hand_r'],:7],hand_to_weapon)
    fit_arm(f,'l',compose(weapon,grips['l']))
    return f

def support(f):
    weapon=compose(fk(f)[ix['hand_r'],:7],hand_to_weapon)
    fit_arm(f,'l',compose(weapon,grips['l']))
    return f

idle=support(np.array(base['clips']['idle']['frames'][0]))
clips={}
def attack(label,source_name,start,end,contact,release):
    entry=.16;exit_time=.18;duration=entry+end-start+exit_time;count=2*round(duration*30)+1
    turn=align_cut(source_name,contact)
    first=pose(source_name,start,turn);last=pose(source_name,end,turn)
    frames=[]
    for i in range(count):
        t=duration*i/(count-1)
        if t<entry:f=support(blend(idle,first,smooth(t/entry)))
        elif t>entry+end-start:f=support(blend(last,idle,smooth((t-entry-end+start)/exit_time)))
        else:f=pose(source_name,t-entry+start,turn)
        frames.append(f.tolist())
    clips[label]=dict(source=source_name,source_range=[start,end],rate=60,frames=frames,
                      contact=(entry+contact-start)/duration,release=(entry+release-start)/duration)

attack('Uppercut','PrimaryAttack_A_Slow',.0666667,1.2,.20,.28)
attack('Overhead','PrimaryAttack_C_Slow',0,1.2666667,.20,.29)
clips['DashOverhead']=clips['Overhead']

def spin(t):
    phase=t/source['clips']['PrimaryAttack_D_Slow']['duration']*(len(spin_yaw)-1)
    heading=np.interp(phase,np.arange(len(spin_yaw)),spin_yaw)
    return pose('PrimaryAttack_D_Slow',t,math.pi*.5-heading)

# One complete native performance across the two gameplay turns. Do not loop
# its jump/plant twice. Only global heading is transferred to the actor clock;
# original hip tilt, body height, chest lead and both leg tracks remain intact.
first,last=spin(0),spin(1.4666667)
for label,begin,end,entry,exit_time in [('Whirlwind.Start',0,.14,.12,0),('Whirlwind.Loop',.14,.32,0,0),('Whirlwind.End',.32,1.4666667,0,.16)]:
    # UE's default compression resamples at 30 Hz; 60 Hz clips must end on a
    # whole 30 Hz frame, including this short, non-looping spin segment.
    duration=entry+end-begin+exit_time;count=max(3,2*round(duration*30)+1);frames=[]
    for i in range(count):
        t=duration*i/(count-1)
        if entry and t<entry:f=support(blend(idle,first,smooth(t/entry)))
        elif exit_time and t>entry+end-begin:f=support(blend(last,idle,smooth((t-entry-end+begin)/exit_time)))
        else:f=spin(t-entry+begin)
        frames.append(f.tolist())
    clips[label]=dict(source='PrimaryAttack_D_Slow',source_range=[begin,end],rate=60,frames=frames,contact=.35,release=.65)

result=dict(mesh=d['mesh'],names=names,clips=clips,
            provenance='Epic Games / Paragon Kwang; UE-only; full-body A upward, C downward, D turning slash; no FPS arm motion',
            source_url='https://www.fab.com/listings/f4c67e92-b976-4b5b-ab9f-4c25b010f6f3',blade_map=blade_map.tolist())
(OUT/'adapted-actions.json').write_text(json.dumps(result,separators=(',',':')))
print('KWANG_ADAPTED '+json.dumps({n:dict(source=c['source'],source_range=c['source_range'],frames=len(c['frames'])) for n,c in clips.items()}))
