"""Adapt the imported Wizard take as a complete native drinking arm.

The donor supplies the shoulder/elbow motion and head timing. Preserve native
bone lengths; carry axial rotation in the forearm, with bounded wrist flexion.
The original V7 grip supplies the prop mount, not a first-person wrist path.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonWizardDrink20261010'
data=json.loads((OUT/'inputs.json').read_text())
target=data['target'];names=target['names'];parents=target['parents'];ix={n:i for i,n in enumerate(names)}
ref=np.asarray(target['reference']);idle=np.asarray(target['clips']['idle']['frames'][0])
raw=np.asarray(target['clips']['drink']['frames']);duration=target['clips']['drink']['duration']

def unit(v): return v/max(np.linalg.norm(v),1.e-10)
def rot(q,v): return R.from_quat(q).apply(v)
def mul(a,b): return (R.from_quat(a)*R.from_quat(b)).as_quat()
def inv(q): return R.from_quat(q).inv().as_quat()
def axis(v,t): return R.from_rotvec(unit(v)*t).as_quat()
def ease(t):
    t=np.clip(t,0.,1.);return t*t*(3.-2.*t)
def mixq(a,b,t):
    delta=R.from_quat(b)*R.from_quat(a).inv()
    return (R.from_rotvec(delta.as_rotvec()*t)*R.from_quat(a)).as_quat()
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y))
    return R.from_matrix(np.column_stack([x,y,np.cross(x,y)])).as_quat()
def compose(a,b): return np.r_[a[:3]+rot(a[3:7],b[:3]),mul(a[3:7],b[3:7])]
def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p>=0:
            w[i,:3]=w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
            w[i,3:7]=mul(w[p,3:7],f[i,3:7]);w[i,7:]=w[p,7:]*f[i,7:]
    return w
def descendant(i,ancestor):
    while i>=0:
        if i==ancestor:return True
        i=parents[i]
    return False
def setq(f,b,q,w): f[b,3:7]=mul(inv(w[parents[b],3:7]),q)
def align(a,b):
    a=unit(a);b=unit(b);q=np.r_[np.cross(a,b),1.+np.dot(a,b)]
    if np.linalg.norm(q)<1.e-6: return axis(np.cross(a,[0.,0.,1.]),np.pi)
    return q/np.linalg.norm(q)

bind=fk(ref);u,e,h,head,clav=[ix[n] for n in ('upperarm_l','lowerarm_l','hand_l','head','clavicle_l')]
forearm_axis=unit(ref[h,:3])
helpers=[i for i in range(len(names)) if descendant(i,u) and i not in (e,h) and not descendant(i,h)]
core=[i for i,n in enumerate(names) if n.startswith('spine_') or n.startswith('neck_') or n=='head']
mouth_local=np.array(data['mouth_in_head'])

# Reconstruct the exact V7-to-Jason anatomical mounting convention used by
# FFPSBodyGripRig, using the saved accepted hand source and current profile.
native=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())['bones']
npose={}
for n,b in native.items():
    mat=np.array(b['axes']).T;mat/=np.linalg.norm(mat,axis=0)
    npose[n]=np.r_[b['position'],R.from_matrix(mat).as_quat()]
def palm_points(pose):
    hand=pose['hand_l']
    return np.array([rot(inv(hand[3:7]),pose[n+'_01_l'][:3]-hand[:3]) for n in ('index','middle','pinky')])
a=palm_points(npose);b=palm_points({n:bind[i] for i,n in enumerate(names)})
mount_q=mul(frame(b[1],b[0]-b[2]),inv(frame(a[1],a[0]-a[2])))
mount=np.r_[b.mean(axis=0)-rot(mount_q,a.mean(axis=0)),mount_q]
hand=npose['hand_l'];x=unit(npose['middle_01_l'][:3]-hand[:3])
z=unit(np.cross(npose['index_01_l'][:3]-hand[:3],npose['pinky_01_l'][:3]-hand[:3]));z=unit(z-x*np.dot(z,x))
palm_q=R.from_matrix(np.column_stack([x,np.cross(z,x),z])).as_quat()
palm_in_hand=np.r_[np.zeros(3),mul(inv(hand[3:7]),palm_q)]
motion=json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8-sig'))
tier=json.loads((ROOT/'SourceAssets/Consume20261006/contact-anatomy.json').read_text())['tiers'][0]
prop_q=R.from_euler('x',90,degrees=True).as_quat()
prop=np.r_[np.array(motion['hp_potion']['grip_in_palm'])-rot(prop_q,[0.,0.,tier['grip_height']]),prop_q]
held=compose(mount,compose(palm_in_hand,prop))
rim_in_hand=compose(held,np.r_[tier['rim'],[0.,0.,0.,1.]])[:3]

def fit_rim(f,weight):
    """The forearm, fixed-local wrist and held bottle are one rigid lever.

    Solve shoulder/elbow to the bottle rim rather than forcing a world wrist
    rotation after IK. Every child keeps its complete local relationship.
    """
    w=fk(f);shoulder=w[u,:3];elbow=w[e,:3];wrist=w[h,:3]
    rim=wrist+rot(w[h,3:7],rim_in_hand)
    mouth=w[head,:3]+rot(w[head,3:7],mouth_local)
    goal=rim+(mouth-rim)*weight
    upper_len=np.linalg.norm(elbow-shoulder);lever_len=np.linalg.norm(rim-elbow)
    direction=unit(goal-shoulder)
    distance=np.clip(np.linalg.norm(goal-shoulder),abs(upper_len-lever_len)+.01,(upper_len+lever_len)*.97)
    end=shoulder+direction*distance
    bend=unit((elbow-shoulder)-direction*np.dot(elbow-shoulder,direction))
    along=(upper_len**2-lever_len**2+distance**2)/(2*distance)
    joint=shoulder+direction*along+bend*np.sqrt(max(0.,upper_len**2-along**2))
    upper_delta=align(elbow-shoulder,joint-shoulder)
    upper_q=mul(upper_delta,w[u,3:7])
    lower_q=mul(upper_delta,w[e,3:7])
    transported=rot(upper_delta,rim-elbow)
    lower_q=mul(align(transported,end-joint),lower_q)
    setq(f,u,upper_q,w);setq(f,e,lower_q,fk(f))
    return f

frames=[];rolls=[]
for donor in raw:
    delta=mul(donor[h,3:7],inv(ref[h,3:7]))
    if delta[3]<0:delta=-delta
    rolls.append(2*np.arctan2(np.dot(delta[:3],forearm_axis),delta[3]))
rolls=np.unwrap(rolls)
for i,donor in enumerate(raw):
    progress=i/(len(raw)-1);f=idle.copy();w=fk(donor)
    f[:,:3]=ref[:,:3];f[:,7:]=ref[:,7:];f[ix['pelvis']]=idle[ix['pelvis']];f[ix['root']]=ref[ix['root']]
    for j in core+[clav]:
        gain=.65 if names[j].startswith(('neck_','head')) else .5
        change=mul(donor[j,3:7],inv(raw[0,j,3:7]))
        f[j,3:7]=mul(mixq([0.,0.,0.,1.],change,gain),idle[j,3:7])
    for j in helpers:f[j]=ref[j]
    setq(f,u,w[u,3:7],fk(f))
    f[e,3:7]=donor[e,3:7]
    # Move axial rotation off the wrist. Retain at most 12 degrees there,
    # and smoothly soften the donor's late, stylized side bend.
    roll=rolls[i];remaining=np.deg2rad(12.)*np.tanh(roll/np.deg2rad(12.));moved=roll-remaining
    delta=mul(donor[h,3:7],inv(ref[h,3:7]))
    swing=R.from_quat(mul(inv(axis(forearm_axis,roll)),delta)).as_rotvec()
    angle=np.linalg.norm(swing);limit=np.deg2rad(30.)
    if angle>1.e-8:swing*=limit*np.tanh(angle/limit)/angle
    f[e,3:7]=mul(f[e,3:7],axis(forearm_axis,moved))
    f[h,3:7]=mul(mul(axis(forearm_axis,remaining),R.from_rotvec(swing).as_quat()),ref[h,3:7])
    for j in helpers:
        if parents[j]==e:
            station=np.clip(np.dot(ref[j,:3],forearm_axis)/np.linalg.norm(ref[h,:3]),0.,1.)
            f[j,3:7]=mul(axis(forearm_axis,-moved*(1.-station)),ref[j,3:7])
    contact=ease((progress-.075)/(.4-.075))*(1.-ease((progress-.75)/(1.-.75)))
    frames.append(fit_rim(f,contact))

frames=np.asarray(frames)
for i in range(1,len(frames)):
    flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0.;frames[i,flip,3:7]*=-1.
result=dict(mesh=target['mesh'],names=names,
    clips={'Consume.Drink':dict(rate=60,contact=.4,release=.75,frames=frames.tolist(),source=data['source']['clips']['drink']['asset'])},
    source_url=data['source_url'],retarget_asset=data['retarget_asset'],
    provenance='Dungeon Mason Wizard for Battle PBR PotionDrinkAnim; native Jason arm adaptation',
    grip_mount=held.tolist(),rim_in_hand= rim_in_hand.tolist(),mouth_in_head=data['mouth_in_head'],
    scope='Third-person drink only. Existing V7 fingers, prop mount, consumption clock and first-person motion retained.',
    parameters={'wrist_twist_limit_degrees':12.,'wrist_swing_soft_limit_degrees':30.,'source_duration':duration},
    gameplay_tested=False,rendered=False)
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('WIZARD_DRINK_AUTHORED',len(frames),'frames; retained complete left arm and native lengths')
