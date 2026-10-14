"""Fit the actual UAL2 left-hand Consume motion to Jason's lips and held props.

The full-body donor supplies torso/neck motion, lift/hold/recovery and elbow
planes. Only prop orientation and mouth contact are adapted. First-person
attack/consume arm paths are never baked into this body animation.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
# Shared rigid-transform / fixed-bone-length math, with no authoring on import.
spec=importlib.util.spec_from_file_location('body_rig_math',OUT.parent/'ThirdPersonSwordDonorRepair20261006/adapt_donor.py')
rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
d=json.loads((OUT/'donor.json').read_text())['target']
names=d['names'];ix={n:i for i,n in enumerate(names)};ref=np.array(d['reference'])
if names!=rig.names:raise RuntimeError('Body rig changed; refresh grip authoring input')
bind=rig.fk(ref)
anatomy=json.loads((OUT/'contact-anatomy.json').read_text())
mouth=np.mean([anatomy['anatomy']['FACIAL_C_LipUpper'],anatomy['anatomy']['FACIAL_C_LipLower']],axis=0)
mouth += [0,.65,0]  # Remain at the lip surface, not inside the closed face.
mouth_local=rig.rot(rig.inv(bind[ix['head'],3:7]),mouth-bind[ix['head'],:3])
native=json.loads((ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())['bones']
npose={}
for n,b in native.items():
    mat=np.array(b['axes']).T
    mat/=np.linalg.norm(mat,axis=0)
    npose[n]=np.r_[b['position'],R.from_matrix(mat).as_quat()]
hand=npose['hand_l']
def anatomical_points(w):
    h=w['hand_l']
    return np.array([rig.rot(rig.inv(h[3:7]),w[n+'_01_l'][:3]-h[:3]) for n in ('index','middle','pinky')])
a=anatomical_points(npose);b=anatomical_points({n:bind[i] for n,i in ix.items()})
mount_q=rig.mul(rig.frame_xy(b[1],b[0]-b[2]),rig.inv(rig.frame_xy(a[1],a[0]-a[2])))
mount=np.r_[b.mean(axis=0)-rig.rot(mount_q,a.mean(axis=0)),mount_q]
x=rig.unit(npose['middle_01_l'][:3]-hand[:3])
z=rig.unit(np.cross(npose['index_01_l'][:3]-hand[:3],npose['pinky_01_l'][:3]-hand[:3]))
z=rig.unit(z-x*np.dot(z,x))
palm_q=R.from_matrix(np.column_stack((x,np.cross(z,x),z))).as_quat()
palm_in_hand=np.r_[np.zeros(3),rig.mul(rig.inv(hand[3:7]),palm_q)]
upright=R.from_euler('x',-90,degrees=True).as_quat()
motion=json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text(encoding='utf-8-sig'))
food=json.loads((OUT/'food-geometry.json').read_text())

def prop_in_hand(profile,height):
    q=rig.inv(upright)
    prop=np.r_[np.array(profile['grip_in_palm'])-rig.rot(q,[0,0,height]),q]
    return rig.compose(mount,rig.compose(palm_in_hand,prop))

def author(label,profile,height,rim):
    held=prop_in_hand(profile,height)
    rim_in_hand=rig.compose(held,np.r_[rim,[0,0,0,1]])[:3]
    frames=[]
    for i in range(41):
        t=i/30
        f=rig.sample(d['clip'],t)
        # Keep all neck and limb lengths, and all non-root scales, on Jason.
        hip=f[ix['pelvis'],:3].copy();f[:,:3]=ref[:,:3];f[:,7:]=ref[:,7:]
        f[ix['pelvis'],:3]=hip;f[ix['root']]=ref[ix['root']]
        w=rig.fk(f)
        wrist=w[ix['hand_l'],:7].copy()
        drink=label=='Drink'
        tilt=float(np.interp(t,[0,.20,.40,.70,.93,1.14,4/3],
            [0,8,104,111,111,20,0] if drink else [0,10,61,65,65,20,0]))
        prop_q=(R.from_euler('z',90,degrees=True)*R.from_euler('y',-tilt,degrees=True)).as_quat()
        grip_q=rig.mul(prop_q,rig.inv(held[3:7]))
        wrist[3:7]=rig.slerp(wrist[3:7],grip_q,rig.smooth(t/.10)*(1-rig.smooth((t-1.23)/(.1033333))))
        contact=rig.smooth((t-.10)/.30)*(1-rig.smooth((t-.93)/(4/3-.93)))
        # The donor starts its empty hand beside the pelvis. Move the prop's
        # carry position in front of Jason's clothes before joining its lift.
        wrist[:3] += [16,29,4]
        goal=w[ix['head'],:3]+rig.rot(w[ix['head'],3:7],mouth_local)
        contact_wrist=goal-rig.rot(wrist[3:7],rim_in_hand)
        wrist[:3]=wrist[:3]*(1-contact)+contact_wrist*contact
        # Transfer the donor elbow plane into the contacted pose, not a fixed
        # camera-space elbow pole. The other arm is excluded at runtime.
        pole=w[ix['lowerarm_l'],:3]-w[ix['upperarm_l'],:3]
        rig.two_bone(f,'l',wrist,pole)
        frames.append(f)
    frames=np.array(frames)
    for i in range(1,len(frames)):
        flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0
        frames[i,flip,3:7]*=-1
    return dict(rate=30,contact=.4/(4/3),release=(28/30)/(4/3),frames=frames.tolist())

common=anatomy['tiers'][0]
clips={'Drink':author('Drink',motion['hp_potion'],common['grip_height'],common['rim'])}
for label,key in [('EatBread','bread'),('EatBaguette','baguette_bread')]:
    mesh=food[key];rim=np.array(mesh['origin'])+np.array([0,0,mesh['extent'][2]])
    clips[label]=author(label,motion[key],mesh['origin'][2],rim)
result=dict(mesh=d['mesh'],skeleton=d['skeleton'],names=names,clips=clips,mouth_in_head=mouth_local.tolist(),
    provenance='Quaternius UAL2 Standard CC0 Consume; retargeted body/left arm with prop and lip contact fit',
    source_asset=d['clip']['asset'],source_url='https://quaternius.itch.io/universal-animation-library-2')
(OUT/'authored-body.json').write_text(json.dumps(result,separators=(',',':')))
print('CONSUME_BODY_AUTHORED '+json.dumps(dict(clips=list(clips),mouth_in_head=mouth_local.tolist())))
