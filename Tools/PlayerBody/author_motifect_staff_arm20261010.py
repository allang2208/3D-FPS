"""Retarget Motifect's actual right shoulder/elbow motion onto native Jason.

Keep native lengths and a neutral wrist. The existing equipped finger layer and
staff mount remain the consumers of the resulting hand; neither is reauthored.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffMotifect20261010'
source=json.loads((OUT/'source-poses.json').read_text())['cast_fireball']
target=json.loads((ROOT/'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
names=target['names']; parents=target['parents']; ix={n:i for i,n in enumerate(names)}
ref=np.array(target['reference']); idle=np.array(target['idle']['frames'][0])
sx={n:i for i,n in enumerate(source['names'])}
C=np.diag([1.,-1.,1.]) # Blender forward -Y to Jason forward +Y.
raw=np.array(source['frames_world']); sr=np.array(source['reference_world'])
points=raw[:,:,:3]@C
source_rot=C@R.from_quat(raw[:,:,3:7].reshape(-1,4)).as_matrix().reshape(*raw.shape[:2],3,3)@C
source_bind_rot=C@R.from_quat(sr[:,3:7]).as_matrix()@C

def unit(v): return v/max(np.linalg.norm(v),1e-10)
def mul(a,b): return (R.from_quat(a)*R.from_quat(b)).as_quat()
def inv(q): return R.from_quat(q).inv().as_quat()
def rot(q,v): return R.from_quat(q).apply(v)
def axis(v,t): return R.from_rotvec(unit(v)*t).as_quat()
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
def blend(a,b,t):
    f=a*(1-t)+b*t;q=a[:,3:7];r=b[:,3:7]
    r=np.where(np.sum(q*r,axis=1,keepdims=True)<0,-r,r)
    angle=np.arccos(np.clip(np.sum(q*r,axis=1,keepdims=True),-1,1))
    sine=np.sin(angle);den=np.where(sine<1e-6,1,sine)
    f[:,3:7]=np.where(sine<1e-6,q*(1-t)+r*t,(q*np.sin((1-t)*angle)+r*np.sin(t*angle))/den)
    f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1,keepdims=True)
    return f
def ease(t): return t*t*(3-2*t)

bind=fk(ref);base=fk(idle)
u,e,h=[ix[n] for n in ['upperarm_r','lowerarm_r','hand_r']]
clav=ix['clavicle_r']; su,se,sh=[sx[n] for n in ['RightArm','RightForeArm','RightHand']]
native_upper=unit(bind[e,:3]-bind[u,:3]);native_lower=unit(bind[h,:3]-bind[e,:3])
native_normal=unit(np.cross(native_upper,native_lower))
lower_axis=unit(ref[h,:3])
# The accepted hand/staff relationship is retained verbatim. It is used once
# to choose the forearm's carry roll, never as a per-frame world wrist target.
accepted=json.loads((ROOT/'SourceAssets/ThirdPersonStaffSurfaceRepair20261009/FinalCheck/poses.json').read_text())['samples'][0]
staff_in_hand=mul(inv(np.array(accepted['bones']['hand_r'][3:7])),np.array(accepted['staff'][3:7]))
source_transverse=source_bind_rot[se].T@(C@(sr[sx['RightHandIndex1'],:3]-sr[sx['RightHandPinky1'],:3]))
rolls=[]
for i,p in enumerate(points):
    upper=unit(p[se]-p[su]);lower=unit(p[sh]-p[se]);normal=unit(np.cross(upper,lower))
    transverse=unit(source_rot[i,se]@source_transverse)
    transverse=unit(transverse-lower*np.dot(transverse,lower))
    rolls.append(np.arctan2(np.dot(np.cross(normal,transverse),lower),np.dot(normal,transverse)))
rolls=np.unwrap(rolls)
frames=[];carry_roll=None
for i,p in enumerate(points):
    f=idle.copy()
    for b in range(len(names)):
        if descendant(b,u) and b not in (e,h) and not descendant(b,h):f[b]=ref[b]
    upper=unit(p[se]-p[su]);lower=unit(p[sh]-p[se]);normal=unit(np.cross(upper,lower))
    upper_q=mul(mul(frame(upper,normal),inv(frame(native_upper,native_normal))),bind[u,3:7])
    lower_q=mul(mul(frame(lower,normal),inv(frame(native_lower,native_normal))),bind[e,3:7])
    if carry_roll is None:
        shaft=rot(mul(mul(lower_q,ref[h,3:7]),staff_in_hand),np.array([0.,0.,1.]))
        a=unit(shaft-lower*np.dot(shaft,lower));b=unit(np.array([0.,0.,1.])-lower*lower[2])
        carry_roll=np.arctan2(np.dot(np.cross(a,b),lower),np.dot(a,b))
    roll=carry_roll+rolls[i]-rolls[0]
    # Carry the original clavicle lift into Jason's native shoulder proportions.
    sc=sx['RightShoulder'];source_delta=source_rot[i,sc]@source_rot[0,sc].T
    setq(f,clav,mul(R.from_matrix(source_delta).as_quat(),base[clav,3:7]))
    setq(f,u,upper_q);setq(f,e,mul(axis(lower,roll),lower_q))
    f[h]=ref[h] # neutral local wrist, entire arm now drives the shaft
    for b,parent in enumerate(parents):
        if parent==e and b!=h:
            station=np.clip(np.dot(ref[b,:3],lower_axis)/np.linalg.norm(ref[h,:3]),0.,1.)
            f[b,3:7]=mul(axis(lower_axis,-roll*(1-station)),ref[b,3:7])
    frames.append(f)

# Use the actual opening arm stance. The source has no staff idle loop: a
# short closing blend makes this selected quiet opening into a carry cycle.
carry=[f.copy() for f in frames[:13]]
for i in range(1,13):carry.append(blend(frames[12],frames[0],ease(i/12)))
# Source 0..46 is the preparation; 46..86 contains extension and follow-through.
# Existing spell gameplay timing remaps these authored phases at runtime.
release_start,release_end=46,86
reach=np.linalg.norm(points[:,sh]-points[:,su],axis=1)
contact=release_start+int(np.argmax(reach[release_start:release_end+1]))
clips={
 'Staff.NativeArm.Carry':dict(frames=carry,range=[0,12],loop=True),
 'Staff.NativeArm.CastGather':dict(frames=frames[:release_start+1],range=[0,release_start],loop=False),
 'Staff.NativeArm.CastRelease':dict(frames=frames[release_start:release_end+1],range=[release_start,release_end],loop=False,
     contact=(contact-release_start)/(release_end-release_start)),
}
for clip in clips.values():
    clip['frames']=np.asarray(clip['frames']).tolist();clip['rate']=30;clip['source']=source['source']
result=dict(mesh=target['mesh'],names=names,clips=clips,provenance='Motifect Fantasy & Magic Motion Pack; cast_fireball; right arm only',
    source_url='https://www.fab.com/listings/b775c780-309f-4cd9-a3f1-e50f7c912b37',
    contact_source_frame=contact,carry_roll_degrees=float(np.rad2deg(carry_roll)),
    scope='Native right shoulder/elbow/forearm motion. Existing fingers, staff mount and independent left hand retained.',
    runtime_tested=False)
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('MOTIFECT_ARM_AUTHORED',json.dumps({k:len(v['frames']) for k,v in clips.items()}),'contact',contact,'roll',np.rad2deg(carry_roll))
