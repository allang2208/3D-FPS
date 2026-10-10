"""Adapt local KayKit punches/chop to Jason's reach and fitted staff palm.

Remove donor lunge/root displacement, retain torso effort and arm timing,
mirror the complete punch through native bind bases, and leave live fingers
to the existing native fist/grip layers. Does not launch or render the game.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from staff_arm_fit import fit as fit_staff_arm

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffCombat20261009'
d=json.loads((OUT/'donors.json').read_text())
spec=importlib.util.spec_from_file_location('body_rig_math',ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006/adapt_donor.py')
rig=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rig)
names=d['names'];ix={n:i for i,n in enumerate(names)}
ref=np.array(d['reference']);parents=d['parents']
rig.names,rig.parents,rig.ix,rig.ref=names,parents,ix,ref
rig.bind=rig.fk(ref)
idle=np.array(d['idle']['frames'][0])
hip=ix['pelvis']
grip=json.loads((ROOT/'SourceAssets/ThirdPersonStaffGripFacing20261009/authored-grip.json').read_text())
staff_q=(R.from_euler('z',90,degrees=True)*R.from_matrix(np.array(grip['variants']['false']['hand_in_grip'])[:3,:3])).as_quat()

def body_frame(raw,start):
    f=idle.copy()
    # Keep Jason's limb lengths and bind scales, with the live legs supplying
    # stance/locomotion. Retain the source's relative torso/neck effort only.
    f[:,:3]=ref[:,:3];f[:,7:]=ref[:,7:]
    f[hip,:3]=idle[hip,:3];f[ix['root']]=ref[ix['root']]
    for n in ('spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head','clavicle_r','clavicle_l'):
        if n not in ix: continue
        i=ix[n]
        delta=rig.mul(raw[i,3:7],rig.inv(start[i,3:7]))
        f[i,3:7]=rig.mul(rig.slerp(np.array([0.,0.,0.,1.]),delta,.65),idle[i,3:7])
    return f

def author(label,key):
    clip=d['clips'][key];source=np.array(clip['frames'])
    start=rig.fk(source[0]);frames=[]
    for raw in source:
        world=rig.fk(raw);f=body_frame(raw,source[0])
        for side in ('r','l'):
            hand=ix['hand_'+side];shoulder=ix['upperarm_'+side];elbow=ix['lowerarm_'+side]
            displacement=(world[hand,:3]-world[hip,:3])-(start[hand,:3]-start[hip,:3])
            if label=='StaffStrike':
                if side=='r':
                    point=np.array([-27.,29.,128.])*np.array([.9066,.95,.9588])+displacement*np.array([.55,.75,.85])
                    q=rig.mul(rig.mul(world[hand,3:7],rig.inv(start[hand,3:7])),staff_q)
                else:
                    point=np.array([24.,15.,102.])+displacement*.35
                    q=rig.fk(idle)[hand,3:7]
            else:
                point=np.array([-24.,32.,129.] if side=='r' else [25.,35.,125.])+displacement*np.array([.65,.55,.65] if side=='r' else [.35,.35,.35])
                q=world[hand,3:7]
            pole=world[elbow,:3]-world[shoulder,:3]
            if label=='StaffStrike' and side=='r':fit_staff_arm(rig,f,point,q,pole)
            else:rig.two_bone(f,side,np.r_[point,q],pole)
        frames.append(f)
    frames=np.array(frames)
    return dict(rate=60,contact=(.6333333333 if label=='StaffStrike' else .5166666667)/clip['duration'],
        release=(.7166666667 if label=='StaffStrike' else .65)/clip['duration'],
        source=clip['source'],source_duration=clip['duration'],frames=frames)

def mirror(clip):
    # Mirroring quaternion components alone would use the wrong left-hand
    # bone axes. Reflect each bone's component-space delta from its own bind.
    mirror=np.diag([-1.,1.,1.])
    bind=rig.bind
    out=[]
    def opposite(n):
        return n[:-2]+'_l' if n.endswith('_r') else n[:-2]+'_r' if n.endswith('_l') else n
    for original in clip['frames']:
        source=rig.fk(original);f=original.copy()
        desired=[]
        for i,n in enumerate(names):
            j=ix.get(opposite(n),i)
            delta=R.from_quat(source[j,3:7]).as_matrix()@R.from_quat(bind[j,3:7]).as_matrix().T
            desired.append(R.from_matrix(mirror@delta@mirror@R.from_quat(bind[i,3:7]).as_matrix()).as_quat())
        for i,p in enumerate(parents):
            f[i,3:7]=rig.mul(rig.inv(desired[p]),desired[i]) if p>=0 else desired[i]
        for side,other in [('l','r'),('r','l')]:
            h=ix['hand_'+side];s=ix['upperarm_'+other];e=ix['lowerarm_'+other]
            rig.two_bone(f,side,np.r_[mirror@source[ix['hand_'+other],:3],desired[h]],mirror@(source[e,:3]-source[s,:3]))
        out.append(f)
    return {**clip,'mirrored':True,'frames':np.array(out)}

right=author('PunchRight','KayKit.Punch')
clips={'Unarmed.FullBody.PunchRight':right,'Unarmed.FullBody.PunchLeft':mirror(right),
       'Staff.FullBody.Strike':author('StaffStrike','KayKit.Chop')}
for c in clips.values():
    frames=c['frames']
    for i in range(1,len(frames)):
        flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0
        frames[i,flip,3:7]*=-1
    c['frames']=frames.tolist()
result=dict(mesh=d['mesh'],names=names,clips=clips,staff_reference_rotation=staff_q.tolist(),
    provenance='Kay Lousberg KayKit Character Animations 1.1, CC0; native Jason reach/torso adaptation; no root motion',
    license_file='SourceAssets/ThirdPersonSwordFree20261005/KayKit/KayKit_Character_Animations_1.1/License.txt',
    source_url='https://kaylousberg.itch.io/kaykit-character-animations')
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
header='#pragma once\n#include "CoreMinimal.h"\n\n// Generated by Tools/PlayerBody/author_staff_combat20261009.py.\nnamespace FPSBodyHandAttackData\n{\ninline const FQuat StaffReferenceRotation('+','.join(f'{v:.12f}' for v in staff_q)+');\n}\n'
(ROOT/'Source/FPSGAME/Characters/FPSBodyHandAttackData.h').write_text(header)
print('STAFF_COMBAT_AUTHORED '+json.dumps({k:len(c['frames']) for k,c in clips.items()}))
