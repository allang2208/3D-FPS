"""Author the user's side-on photo grip: spine presented, cover receding away.

Production authoring only: joint rotations and one rigid book-in-hand mount.
Native bind matrices, weights, bone lengths and the existing gait stay intact.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v): return np.asarray(v) / np.linalg.norm(v)
def mat(q, p):
    m = np.eye(4); m[:3, :3] = q; m[:3, 3] = p; return m
native = read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')
anatomy = read(ROOT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']['l']
bones = native['bones']; order = sorted(bones, key=lambda n: bones[n]['index'])
by_index = {b['index']: n for n,b in bones.items()}
parent = {n: by_index.get(bones[n]['parent']) for n in order}
rest = {}
for n in order:
    q = np.array(bones[n]['axes']).T; q /= np.linalg.norm(q, axis=0)
    rest[n] = mat(R.from_matrix(q).as_matrix(), bones[n]['position'])
local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] if parent[n] else rest[n] for n in order}
def child(n, ancestor):
    while parent[n]:
        n = parent[n]
        if n == ancestor: return True
    return False
fingers = [n for n in order if child(n, 'hand_l')]
# Keep the existing clamp as one rigid book/hand relationship. The user's
# correction concerns the cover presentation, so do not refit fingers into a
# different grasp simply to turn the book sideways.
previous = read(P.parent/'GripPhotoV2/grip.json')
mount = np.array(previous['book_in_hand'])
hand_in_book = np.array(previous['hand_in_book'])
q = {n:np.array(previous['fingers'][n])[:3,:3] for n in fingers}
f=np.array(anatomy['forward']); d=np.array(anatomy['dorsal'])

def frame(forward,dorsal):
    x=unit(forward);z=unit(dorsal-x*np.dot(x,dorsal))
    return np.column_stack((x,np.cross(z,x),z))

def swing(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1.e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()

# Photo semantics: +X into the scene, +Y screen-right, +Z up. The spine
# faces the eye, the fore-edge recedes away and down/right, and the top leans
# right. Single-photo depth is an authored estimate, not a measured pose.
book_up=unit([.22,.50,.837])
book_front=unit(np.array([-.40,.82,-.45])-book_up*np.dot(book_up,[-.40,.82,-.45]))
book_camera=np.column_stack((np.cross(-book_up,book_front),-book_up,book_front))
target_hand_camera=book_camera@hand_in_book[:3,:3]

# Retain the accepted gait's wrist path, shoulder lead, phase and 32 samples.
# Author the supporting elbow/forearm around the photo palm, with the native
# lengths and helpers; no isolated wrist twist or runtime vertex fitting.
source=read(ROOT/'SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/full-pose.json')
gait=read(ROOT/'SourceAssets/ApprenticeStaff20260927/LeftGaitV16/left-gait.json')
arm_names=gait['order']
idle_source={n:np.array(v) for n,v in source['poses']['false'][0]['component'].items()}
ru=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3]
rl=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
length_u,length_l=np.linalg.norm(ru),np.linalg.norm(rl)
framing_offset=np.array([6.,0.,7.])
def author_arm(src):
    h_rotation=src['hand_l'][:3,:3]@idle_source['hand_l'][:3,:3].T@target_hand_camera
    wrist=src['hand_l'][:3,3]+framing_offset
    shoulder=src['upperarm_l'][:3,3]
    reach=wrist-shoulder;length=np.linalg.norm(reach);axis=unit(reach)
    along=(length_u**2-length_l**2+length**2)/(2*length)
    circle=shoulder+axis*along
    h_deform=h_rotation@rest['hand_l'][:3,:3].T
    ideal_elbow=wrist-h_deform@rl
    pole=.82*ideal_elbow+.18*src['lowerarm_l'][:3,3]
    bend=unit(pole-circle-axis*np.dot(pole-circle,axis))
    elbow=circle+bend*math.sqrt(max(0.,length_u**2-along**2))
    lower_delta=frame(wrist-elbow,h_deform@d)@frame(rl,d).T
    upper_delta=swing(lower_delta@ru,elbow-shoulder)@lower_delta
    w={n:m.copy() for n,m in rest.items()}
    w['upperarm_l']=mat(upper_delta@rest['upperarm_l'][:3,:3],shoulder)
    w['lowerarm_l']=mat(lower_delta@rest['lowerarm_l'][:3,:3],elbow)
    w['hand_l']=mat(h_rotation,wrist)
    w['clavicle_l']=src['clavicle_l'].copy()
    w['clavicle_l'][:3,3]=shoulder-w['clavicle_l'][:3,:3]@local['upperarm_l'][:3,3]
    for n in arm_names:
        if n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'):continue
        segment=mat(q[n],local[n][:3,3]) if n in q else local[n]
        w[n]=w[parent[n]]@segment
    return {'local':{n:(np.linalg.inv(w[parent[n]])@w[n]).tolist() for n in arm_names},
            'component':{n:w[n].tolist() for n in arm_names}}
poses=[author_arm(idle_source)]
for cycle in ('Walk','Run'):
    for sample in gait['cycles'][cycle]:
        poses.append(author_arm({n:np.array(v) for n,v in sample['component'].items()}))
result={'revision':3,'reference':'user photo codex-clipboard-2a10d056-dfcc-46ca-879b-98d2ee77c3c7.jpg',
        'intent':'spine toward eye; cover receding sideways; top leaning right; dorsal toward player; thumb front and four fingers behind spine',
        'authored_book_camera_basis':book_camera.tolist(),
        'units':'UE cm','book_in_hand':mount.tolist(),'hand_in_book':hand_in_book.tolist(),
        'fingers':{n:mat(q[n],local[n][:3,3]).tolist() for n in fingers},'controls':previous['controls'],'controls_radians':previous['controls_radians'],
        'arm_order':arm_names,'poses':poses,'gait_source':'LeftGaitV16/left-gait.json','framing_offset_cm':framing_offset.tolist(),
        'skin_pad_vertex_ids':previous['skin_pad_vertex_ids'],
        'grasp_source':'GripPhotoV2/grip.json; book mount and finger rotations preserved',
        'runtime_tested':False,'rendered':False}
(P/'grip.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
def vec(v):return ','.join(f'{x:.10f}' for x in v)
def quat(m):return f'FQuat({vec(R.from_matrix(m[:3,:3]).as_quat())})'
header=['#pragma once','#include "CoreMinimal.h"','// Generated by SourceAssets/SpellbookEvildeer20261009/GripPhotoV3/author_grip.py.',
    'namespace SpellbookAuthoredGrip {','inline constexpr int32 Revision=3, Samples=32, PoseCount=65, BoneCount='+str(len(arm_names))+';',
    'struct FBone { const TCHAR* Name; FQuat Rotation; };','struct FArmBone { FQuat Rotation; FVector Position; };',
    f'inline const FTransform BookInHand=FTransform({quat(mount)},FVector({vec(mount[:3,3])}));','inline const FBone Fingers[]={']
header += [f'    {{TEXT("{n}"),{quat(mat(q[n],local[n][:3,3]))}}},' for n in fingers]
header += ['};','inline const TCHAR* ArmNames[]={'+','.join(f'TEXT("{n}")' for n in arm_names)+'};','inline const FArmBone Poses[PoseCount][BoneCount]={']
for pose_key in poses:
    header.append('{')
    for n in arm_names:
        m=np.array(pose_key['local'][n]);header.append(f'    {{{quat(m)},FVector({vec(m[:3,3])})}},')
    header.append('},')
header += ['};','}']
dest=ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredGrip.h'
dest.write_text('\n'.join(header)+'\n',encoding='utf-8')
print('Authored side-on photo carry: 65 native arm poses; V2 clamp preserved; book basis:',book_camera.tolist(),flush=True)
