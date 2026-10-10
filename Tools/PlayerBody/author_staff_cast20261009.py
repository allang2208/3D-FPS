"""Fit KayKit's full arm casting motion to Jason and the VRE staff palm.

The donor supplies shoulder effort, lift/forward timing and elbow direction.
Keep native lengths and helper locals; fit elbow swivel to the real held palm.
Only the final native rotations are animated at runtime, with the staff attached
to that wrist. No camera-space contact curve drives the third-person arm.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffCast20261009'
d=json.loads((OUT/'donors.json').read_text())
spec=importlib.util.spec_from_file_location('body_rig_math',ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006/adapt_donor.py')
rig=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rig)
names=d['names'];ix={n:i for i,n in enumerate(names)}
ref=np.array(d['reference']);parents=d['parents']
rig.names,rig.parents,rig.ix,rig.ref=names,parents,ix,ref
rig.bind=rig.fk(ref)
idle=np.array(d['idle']['frames'][0]);hip=ix['pelvis']
hand,upper,lower=[ix[n] for n in ('hand_r','upperarm_r','lowerarm_r')]
grip=json.loads((ROOT/'SourceAssets/ThirdPersonStaffGripFacing20261009/authored-grip.json').read_text())
staff_q=(R.from_euler('z',90,degrees=True)*R.from_matrix(np.array(grip['variants']['false']['hand_in_grip'])[:3,:3])).as_quat()
carry=np.array([-27.,29.,128.])*np.array([.9066,.95,.9588])

def axis_rotation(direction):
    return R.from_rotvec(np.cross([0.,0.,1.],rig.unit(direction))*
        (np.arccos(rig.unit(direction)[2])/max(np.linalg.norm(np.cross([0.,0.,1.],rig.unit(direction))),1e-9))).as_quat()
raised_q=rig.mul(axis_rotation([.10,.52,.848]),staff_q)
contact_q=rig.mul(axis_rotation([.08,.94,.332]),staff_q)
follow_q=rig.mul(axis_rotation([.10,.96,.262]),staff_q)

def body(raw,start):
    f=idle.copy();f[:,:3]=ref[:,:3];f[:,7:]=ref[:,7:]
    f[hip,:3]=idle[hip,:3];f[ix['root']]=ref[ix['root']]
    for n in ('spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head','clavicle_r'):
        if n in ix:
            i=ix[n];delta=rig.mul(raw[i,3:7],rig.inv(start[i,3:7]))
            f[i,3:7]=rig.mul(rig.slerp(np.array([0.,0.,0.,1.]),delta,.65),idle[i,3:7])
    # Keep twist/corrective bones on the same native segment as their parent.
    for i,n in enumerate(names):
        if n.endswith('_r') and any(s in n for s in ('twist','corrective','upperarm_','lowerarm_')):
            f[i]=ref[i]
    return f

from staff_arm_fit import fit as fit_arm

def fit(f,point,q,pole,previous):
    return fit_arm(rig,f,point,q,pole)

g=d['clips']['Gather'];source=np.array(g['frames']);start=rig.fk(source[0])
# Trim the donor's sustained loop and return; gameplay owns both hold and return.
gather_end=39
frames=[]
for i,raw in enumerate(source[:gather_end+1]):
    w=rig.fk(raw)
    displacement=(w[hand,:3]-w[hip,:3])-(start[hand,:3]-start[hip,:3])
    point=carry+displacement*np.array([.10,.25,.55])
    q=rig.slerp(staff_q,raised_q,rig.smooth(i/gather_end))
    f=fit(body(raw,source[0]),point,q,w[lower,:3]-w[upper,:3],frames[-1] if frames else None)
    frames.append(f)
gather=np.array(frames);raised_world=rig.fk(gather[-1]);raised=raised_world[hand,:3]
raised_pole=rig.unit(raised_world[lower,:3]-raised_world[upper,:3])

c=d['clips']['Release'];source=np.array(c['frames']);world=np.array([rig.fk(f) for f in source]);start=world[0]
forward=world[:,hand,1]-world[:,hip,1]
contact=int(np.argmax(forward[:24]));release_end=min(contact+6,len(source)-1)
frames=[]
for i,raw in enumerate(source[:release_end+1]):
    w=world[i];disp=(w[hand,:3]-w[hip,:3])-(start[hand,:3]-start[hip,:3])
    point=raised+disp*np.array([.20,.35,-.55])
    if i<=contact:q=rig.slerp(raised_q,contact_q,rig.smooth(i/max(contact,1)))
    else:q=rig.slerp(contact_q,follow_q,rig.smooth((i-contact)/(release_end-contact)))
    f=body(raw,source[0])
    # Preserve the exact lifted shoulder/chest at the phase boundary.
    for n in ('spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head','clavicle_r'):
        if n in ix:
            j=ix[n];delta=rig.mul(f[j,3:7],rig.inv(idle[j,3:7]));f[j,3:7]=rig.mul(delta,gather[-1,j,3:7])
    # Transport the actual raised elbow plane into the donor's forward pose.
    # Changing to the shoot take's idle elbow on frame one would break the seam.
    pole=raised_pole*(1-rig.smooth(i/max(contact,1)))+rig.unit(w[lower,:3]-w[upper,:3])*rig.smooth(i/max(contact,1))
    f=fit(f,point,q,pole,frames[-1] if frames else gather[-1])
    # The first frame is shared in full, including elbow roll and helper bones.
    if i==0:f=gather[-1].copy()
    frames.append(f)
release=np.array(frames)
clips={
    'Staff.FullBody.CastGather':dict(rate=60,contact=1.,release=1.,source=g['source'],source_range=[0,gather_end/60],frames=gather),
    'Staff.FullBody.CastRelease':dict(rate=60,contact=contact/release_end,release=1.,source=c['source'],source_range=[0,release_end/60],frames=release)}
for clip in clips.values():
    f=clip['frames']
    for i in range(1,len(f)):
        flip=np.sum(f[i-1,:,3:7]*f[i,:,3:7],axis=1)<0;f[i,flip,3:7]*=-1
    clip['frames']=f.tolist()
result=dict(mesh=d['mesh'],names=names,clips=clips,staff_reference_rotation=staff_q.tolist(),
    provenance='Kay Lousberg KayKit Character Animations 1.1, CC0; native Jason casting and VRE staff palm adaptation',
    license_file='SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/License.txt',
    source_url='https://kaylousberg.itch.io/kaykit-character-animations',runtime_tested=False,rendered=False)
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
header='#pragma once\n#include "CoreMinimal.h"\n\n// Generated by Tools/PlayerBody/author_staff_cast20261009.py.\nnamespace FPSBodyStaffCastData\n{\ninline const FQuat ReferenceRotation('+','.join(f'{v:.12f}' for v in staff_q)+');\n}\n'
(ROOT/'Source/FPSGAME/Characters/FPSBodyStaffCastData.h').write_text(header)
print('STAFF_CAST_AUTHORED '+json.dumps({k:len(c['frames']) for k,c in clips.items()}))
