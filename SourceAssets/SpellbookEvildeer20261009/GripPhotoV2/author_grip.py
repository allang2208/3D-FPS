"""Author the user's photo grip: thumb on front, four fingers behind the spine.

Production authoring only: joint rotations and one rigid book-in-hand mount.
Native bind matrices, weights, bone lengths and the existing gait stay intact.
"""
import json, math
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v): return np.asarray(v) / np.linalg.norm(v)
def mat(q, p):
    m = np.eye(4); m[:3, :3] = q; m[:3, 3] = p; return m
native = read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')
skin = read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json')
anatomy = read(ROOT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']['l']
bow = read(ROOT/'SourceAssets/DarkBow20260925/GripV5/grasp_native.json')
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
donor = {n: np.array(v) for n,v in bow['pose'].items()}
grip = np.array(bow['grip_in_source'])
hand = np.linalg.inv(grip) @ donor['hand_l']
closed = {n: donor[parent[n]][:3,:3].T @ donor[n][:3,:3] if n in donor and parent[n] in donor else local[n][:3,:3] for n in fingers}
digits = {d['bone']: d for d in anatomy['digits']}
controls = [(n,'flex') for n in fingers if n in digits] + [('thumb_01_l','opposition'),('thumb_01_l','pronation')] + [(n,'splay') for n in fingers if n in digits and digits[n]['segment']==1 and not n.startswith('thumb')]
axes = []
for n,kind in controls:
    d = digits[n]
    axis = unit(np.cross(d['axis'], d['dorsal'])) if kind=='flex' else unit(d['axis']) if kind=='pronation' else unit(d['dorsal']) if kind=='splay' else unit(anatomy['dorsal'])
    hinge = rest[n][:3,:3].T @ axis
    if kind=='flex' and d['segment']>=2:
        bend = R.from_matrix(local[n][:3,:3].T @ closed[n]).as_rotvec()
        if np.linalg.norm(bend)>.01: hinge=unit(bend)
    axes.append(hinge)
weights = skin['weights']; family = {'hand_l', *fingers}
ids = np.array([i for i,w in enumerate(weights) if sum(v for n,v in w.items() if n in family)>.75])
points = np.array(skin['positions'])[ids]; hp = np.column_stack((points, np.ones(len(ids))))
influences = {n: np.array([weights[i].get(n,0) for i in ids]) for n in order}
influences = {n:w for n,w in influences.items() if np.any(w)}
bind = {n: hp @ np.linalg.inv(rest[n]).T for n in influences}
patches = {}
for n,d in digits.items():
    if d['digit']=='thumb' and d['segment']==1: continue
    center = np.array(d['head']) + np.array(d['axis'])*d['length']*.45 - np.array(d['dorsal'])*d['radius']*.78
    if d['digit']=='thumb':
        deform=donor[n][:3,:3] @ rest[n][:3,:3].T
        c=donor[n][:3,3]+deform@np.array(d['axis'])*d['length']*.45
        closest=grip[:3,3]+grip[:3,2]*np.dot(c-grip[:3,3],grip[:3,2])
        pad=deform.T@unit(closest-c)
        center=np.array(d['head'])+np.array(d['axis'])*d['length']*.45+pad*d['radius']*.78
    candidates=np.array([k for k,i in enumerate(ids) if sum(v for b,v in weights[i].items() if b.startswith(d['digit']) and b.endswith('_l'))>.5])
    patches[n]=candidates[np.argsort(np.linalg.norm(points[candidates]-center,axis=1))[:6 if d['digit']=='thumb' else 12]]
wr=rest['hand_l'][:3,3]; f=np.array(anatomy['forward']); a=np.array(anatomy['across']); d=np.array(anatomy['dorsal'])
pc=np.array([k for k,i in enumerate(ids) if sum(v for n,v in weights[i].items() if n=='hand_l' or 'metacarpal_l' in n)>.7])
for name,c in [('palm_radial',wr+f*7+a*1.1-d*.9),('palm_ulnar',wr+f*7-a*1.6-d*.9)]:
    patches[name]=pc[np.argsort(np.linalg.norm(points[pc]-c,axis=1))[:18]]

def frame(forward,dorsal):
    x=unit(forward);z=unit(dorsal-x*np.dot(x,dorsal))
    return np.column_stack((x,np.cross(z,x),z))
def swing(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1.e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()

# Photo semantics in the camera's +X forward, +Y right, +Z up frame.
# The dorsal surface faces the player; the visible thumb presses the illustrated
# cover. The hidden finger pads oppose it on the back cover, beside the spine.
book_up=unit([.12,.38,.917])
book_front=unit(np.array([-.9,.36,.18])-book_up*np.dot(book_up,[-.9,.36,.18]))
book_camera=np.column_stack((np.cross(-book_up,book_front),-book_up,book_front))
target_hand_camera=frame([.66,.35,.66],[-.67,-.23,.70])@frame(f,d).T@rest['hand_l'][:3,:3]
hand_rotation=book_camera.T@target_hand_camera
vertices=np.array(read(P.parent/'source-parts.json')['book2']['vertices'])
lo=vertices.min(axis=0);hi=vertices.max(axis=0);center=(lo+hi)*.5
book=np.column_stack((100*(hi[1]-vertices[:,1]),-100*(vertices[:,2]-center[2]),100*(center[0]-vertices[:,0])))
eq=np.unique(np.round(ConvexHull(book).equations,7),axis=0)
half_thickness=float(book[:,2].max())

def pose(x):
    hand=mat(hand_rotation,x[:3]);world={'hand_l':hand};q={n:closed[n].copy() for n in fingers}
    for i,(n,kind) in enumerate(controls):q[n]=q[n]@R.from_rotvec(axes[i]*x[3+i]).as_matrix()
    for n in fingers:world[n]=world[parent[n]]@mat(q[n],local[n][:3,3])
    fallback=hand@np.linalg.inv(rest['hand_l']);v=np.zeros((len(ids),4))
    for n,w in influences.items():v+=(bind[n]@world.get(n,fallback@rest[n]).T)*w[:,None]
    v=v[:,:3];sd=np.max(v@eq[:,:3].T+eq[:,3],axis=1)
    return world,q,v,sd

def residual(x):
    world,q,v,sd=pose(x);terms=[np.minimum(sd-.06,0)*32]
    for n,p in patches.items():
        thumb=n.startswith('thumb');tip='_03_' in n;middle='_02_' in n
        weight=5. if thumb and tip else .2 if thumb else 1.8 if tip or middle else .4
        terms.append((sd[p]-.12)*weight)
        if tip or (middle and not thumb):
            # Named cover-side contact prevents an equally close but reversed grip.
            z=half_thickness+.12 if thumb else -half_thickness-.12
            terms.append((v[p,2]-z)*(5. if thumb else 2.4 if tip else 1.2))
            terms.append(np.maximum(.7-v[p,0],0)*(3. if tip else .6))
            terms.append(np.maximum(v[p,0]-5.0,0)*.6)
    terms.extend([(x[:3]-[-6.5,6.,4.])*[.4,1.2,.4],x[3:]*.65])
    for digit in ('index','middle','ring','pinky'):
        indices=[i for i,(n,kind) in enumerate(controls) if n.startswith(digit) and kind=='flex']
        terms.append(np.diff(x[3+np.array(indices)])*.5)
    thumb_angle=R.from_matrix(local['thumb_01_l'][:3,:3].T@q['thumb_01_l']).magnitude()
    terms.append(np.array([max(0.,thumb_angle-math.radians(85))*10]))
    return np.concatenate(terms)

angles=np.radians([24 if kind=='splay' else 80 if n.startswith('thumb') else 85 for n,kind in controls])
low=np.r_[[-11,2.,-.5],-angles];high=np.r_[[-2,10.,8.],angles]
# Keep interphalangeal flexion in its anatomical direction. Contact fitting
# cannot buy a smaller distance by folding a distal joint backward.
for i,(n,kind) in enumerate(controls):
    if kind!='flex' or n.startswith('thumb') or digits[n]['segment']<2:continue
    neutral=float(np.dot(R.from_matrix(local[n][:3,:3].T@closed[n]).as_rotvec(),axes[i]))
    upper=math.radians(100 if digits[n]['segment']==2 else 75)
    low[3+i]=max(low[3+i],math.radians(2)-neutral)
    high[3+i]=min(high[3+i],upper-neutral)
solutions=[]
for z in (3.5,6.5):
    start=np.clip(np.r_[[-6.5,6.,z],np.zeros(len(controls))],low+1.e-6,high-1.e-6)
    result=least_squares(residual,start,bounds=(low,high),max_nfev=250,diff_step=1.e-4,ftol=1.e-7,xtol=1.e-7,gtol=1.e-6)
    solutions.append(result)
fit=min(solutions,key=lambda x:x.cost)
world,q,skin_points,sd=pose(fit.x)
mount=np.linalg.inv(world['hand_l'])

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
result={'revision':2,'reference':'user photo codex-clipboard-2a10d056-dfcc-46ca-879b-98d2ee77c3c7.jpg',
        'intent':'dorsal toward player; thumb on front cover; four fingers behind spine; inclined closed book',
        'units':'UE cm','book_in_hand':mount.tolist(),'hand_in_book':world['hand_l'].tolist(),
        'fingers':{n:mat(q[n],local[n][:3,3]).tolist() for n in fingers},'controls':controls,'controls_radians':fit.x[3:].tolist(),
        'arm_order':arm_names,'poses':poses,'gait_source':'LeftGaitV16/left-gait.json','framing_offset_cm':framing_offset.tolist(),
        'skin_pad_vertex_ids':{n:ids[v].tolist() for n,v in patches.items()},
        'production_fit':{'cost':float(fit.cost),'minimum_clearance_cm':float(sd.min()),
            'pad_centers_book_cm':{n:skin_points[v].mean(axis=0).tolist() for n,v in patches.items()}},
        'runtime_tested':False,'rendered':False}
(P/'grip.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
def vec(v):return ','.join(f'{x:.10f}' for x in v)
def quat(m):return f'FQuat({vec(R.from_matrix(m[:3,:3]).as_quat())})'
header=['#pragma once','#include "CoreMinimal.h"','// Generated by SourceAssets/SpellbookEvildeer20261009/GripPhotoV2/author_grip.py.',
    'namespace SpellbookAuthoredGrip {','inline constexpr int32 Revision=2, Samples=32, PoseCount=65, BoneCount='+str(len(arm_names))+';',
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
print('Authored photo grip and 65 native carry/gait poses:',result['production_fit'],flush=True)
