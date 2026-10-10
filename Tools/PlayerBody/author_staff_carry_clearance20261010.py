"""Keep Motifect's joint motion, stage the whole right arm outside the body.

The accepted wrist-to-prop and finger relations are unchanged. The left book
gets a native arm support pose; runtime mixes only a small amount of live gait.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffCarryClearance20261010'
OUT.mkdir(parents=True,exist_ok=True)
original=json.loads((ROOT/'SourceAssets/ThirdPersonStaffMotifect20261010/authored.json').read_text())
target=json.loads((ROOT/'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
scene=json.loads((OUT/'existing-scene.json').read_text())['actors'][0]
staff=next(p for p in scene['parts'] if p['socket']=='hand_r' and 'Staff' in p['mesh'])
book=next(p for p in scene['parts'] if p['socket']=='hand_l' and 'Spellbook' in p['mesh'])
names=target['names'];parents=target['parents'];ix={n:i for i,n in enumerate(names)}
ref=np.asarray(target['reference']);idle=np.asarray(target['idle']['frames'][0])

def unit(v):return v/max(np.linalg.norm(v),1.e-10)
def mul(a,b):return (R.from_quat(a)*R.from_quat(b)).as_quat()
def inv(q):return R.from_quat(q).inv().as_quat()
def rot(q,v):return R.from_quat(q).apply(v)
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y))
    return R.from_matrix(np.column_stack([x,y,np.cross(x,y)])).as_quat()
def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p>=0:
            w[i,:3]=w[p,:3]+rot(w[p,3:7],f[i,:3]*w[p,7:])
            w[i,3:7]=mul(w[p,3:7],f[i,3:7]);w[i,7:]=w[p,7:]*f[i,7:]
    return w
def setq(f,i,q):
    w=fk(f);f[i,3:7]=mul(inv(w[parents[i],3:7]),q)
def descendant(i,ancestor):
    while i>=0:
        if i==ancestor:return True
        i=parents[i]
    return False

u,e,h=[ix[n] for n in ['upperarm_r','lowerarm_r','hand_r']]
first=np.asarray(original['clips']['Staff.NativeArm.Carry']['frames'][0])
base=fk(first)
shaft=rot(mul(base[h,3:7],staff['relative'][3:7]),[0.,0.,1.])
# A fixed shoulder correction preserves every elbow/wrist local and the donor's
# temporal variation. No frame-dependent wrist rotation or elbow-plane flips.
upright=R.align_vectors([[0.,0.,1.]],[shaft])[0]
reach=upright.apply(base[h,:3]-base[u,:3])
opening=R.from_euler('z',np.arctan2(30.,-30.)-np.arctan2(reach[1],reach[0]))
correction=opening*upright
carry_axis=unit(np.array([.24,.05,1.]))
clips={}
for key,clip in original['clips'].items():
    result={k:v for k,v in clip.items() if k!='frames'}
    frames=[]
    for index,raw in enumerate(clip['frames']):
        f=np.asarray(raw).copy();w=fk(f)
        group=correction
        # A long staff magnifies a few degrees of breathing into a large tip
        # sweep. Stage the entire arm toward a consistent carry axis whose
        # lower end points away from the legs, without changing the wrist.
        # Blend this carry constraint out before the donor's release reach.
        weight=1. if key.endswith('.Carry') else 0.
        if key.endswith('.CastGather'):
            t=np.clip((index-32.)/14.,0.,1.);weight=1.-t*t*(3.-2.*t)
        if weight>0:
            current=group.apply(rot(mul(w[h,3:7],staff['relative'][3:7]),[0.,0.,1.]))
            swing=R.align_vectors([carry_axis],[current])[0]
            group=R.from_rotvec(swing.as_rotvec()*weight)*group
        setq(f,u,(group*R.from_quat(w[u,3:7])).as_quat())
        frames.append(f.tolist())
    result['frames']=frames;clips[key]=result

# Jason's native hinge frames, native segment lengths and neutral local wrist.
# The book is supported just forward/outside the left hip with a bent elbow.
lu,le,lh=[ix[n] for n in ['upperarm_l','lowerarm_l','hand_l']]
bind=fk(ref);f=idle.copy()
for b in range(len(names)):
    if descendant(b,lu) and b not in (le,lh) and not descendant(b,lh):f[b]=ref[b]
w=fk(f);shoulder=w[lu,:3]
l1=np.linalg.norm(ref[le,:3]);l2=np.linalg.norm(ref[lh,:3])
hand=shoulder+np.array([18.,23.,-35.])
axis=unit(hand-shoulder);distance=np.linalg.norm(hand-shoulder)
along=(l1*l1-l2*l2+distance*distance)/(2*distance)
pole=np.array([22.,-14.,-30.]);bend=unit(pole-axis*np.dot(pole,axis))
elbow=shoulder+axis*along+bend*np.sqrt(l1*l1-along*along)
upper=unit(elbow-shoulder);lower=unit(hand-elbow);normal=unit(np.cross(upper,lower))
bu=unit(bind[le,:3]-bind[lu,:3]);bl=unit(bind[lh,:3]-bind[le,:3]);bn=unit(np.cross(bu,bl))
setq(f,lu,mul(mul(frame(upper,normal),inv(frame(bu,bn))),bind[lu,3:7]))
setq(f,le,mul(mul(frame(lower,normal),inv(frame(bl,bn))),bind[le,3:7]))
f[lh]=ref[lh]
clips['Staff.BookCarry']=dict(frames=[f.tolist(),f.tolist()],rate=30,range=[0,0],loop=True,
    source='Jason native arm support; original equipped book mount and fingers')
result=dict(mesh=target['mesh'],names=names,clips=clips,source_url=original['source_url'],
    source_parent='SourceAssets/ThirdPersonStaffMotifect20261010/authored.json',
    staff_mount=staff['relative'],book_mount=book['relative'],
    shoulder_correction_quaternion=correction.as_quat().tolist(),
    scope='Whole right-arm staging and independent left book support; no hand/prop mount or finger edits.',
    runtime_tested=False)
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('STAFF_CARRY_AUTHORED',list(clips),'shoulder degrees',np.linalg.norm(correction.as_rotvec())*180/np.pi)
