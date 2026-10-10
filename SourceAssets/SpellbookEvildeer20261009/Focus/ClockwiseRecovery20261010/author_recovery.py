"""V11: accepted spine landing, then screen-clockwise recovery with a supported wrist."""
import json, math, re
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

P=Path(__file__).resolve().parents[1]; ROOT=P.parents[2]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v): return np.asarray(v)/np.linalg.norm(v)
def mat(q,p):
    m=np.eye(4); m[:3,:3]=q; m[:3,3]=p; return m
def mixq(a,b,t): return Slerp([0,1],R.from_matrix([a,b]))([np.clip(t,0,1)]).as_matrix()[0]
def ease(a,b,t):
    t=np.clip((t-a)/(b-a),0,1); return t*t*t*(t*(6*t-15)+10)
def blend(a,b,t): return mat(mixq(a[:3,:3],b[:3,:3],t),(1-t)*a[:3,3]+t*b[:3,3])
def frame(x,z):
    x=unit(x); z=unit(z-x*np.dot(x,z)); return np.column_stack((x,np.cross(z,x),z))
def swing(a,b):
    a,b=unit(a),unit(b); v=np.cross(a,b); s=np.linalg.norm(v)
    return np.eye(3) if s<1.e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()

grip=read(P.parent/'GripPhotoV3/grip.json'); focus=read(P/'focus.json')
landing=read(P/'VideoRecovery20261010/landing-baseline-v9.json')
bones=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')['bones']
anatomy=read(ROOT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']['l']
order=sorted(bones,key=lambda n:bones[n]['index']); byindex={b['index']:n for n,b in bones.items()}
parent={n:byindex.get(bones[n]['parent']) for n in order}; rest={}
for n in order:
    q=np.array(bones[n]['axes']).T; q/=np.linalg.norm(q,axis=0)
    rest[n]=mat(R.from_matrix(q).as_matrix(),bones[n]['position'])
local={n:np.linalg.inv(rest[parent[n]])@rest[n] if parent[n] else rest[n] for n in order}
names=grip['arm_order']; base={n:np.array(v) for n,v in grip['poses'][0]['component'].items()}
base_local={n:np.array(v) for n,v in grip['poses'][0]['local'].items()}
ru=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3]
rl=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
lu,ll=np.linalg.norm(ru),np.linalg.norm(rl); dorsal=np.array(anatomy['dorsal'])
motion=(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookFocusMotion.h').read_text(encoding='utf-8')
def number(name): return float(re.search(r'\b'+name+r'\s*=\s*([0-9.]+)f',motion).group(1))
close,prepare,drop,hold,grip_seconds,settle_seconds=[number(n) for n in ('Close','PalmPrepare','Drop','ContactHold','Grip','Settle')]
drop_start=close+prepare; contact=drop_start+drop; grip_start=contact+hold
grip_end=grip_start+grip_seconds; duration=grip_end+settle_seconds
mount=np.array(grip['book_in_hand']); catch_mount=np.array(landing['catch_book_in_hand'])

def landing_pose(age):
    t=age/landing['seconds']['total']; j=np.searchsorted(landing['times'],t,side='right')-1
    j=max(0,min(j,len(landing['times'])-2)); a=(t-landing['times'][j])/(landing['times'][j+1]-landing['times'][j])
    world={n:m.copy() for n,m in rest.items()}; result={'local':{},'component':{}}
    for n in names:
        m=blend(np.array(landing['poses'][j]['local'][n]),np.array(landing['poses'][j+1]['local'][n]),a)
        world[n]=world[parent[n]]@m; result['local'][n]=m.tolist(); result['component'][n]=world[n].tolist()
    return result

gripped=landing_pose(grip_end)
gw={n:np.array(v) for n,v in gripped['component'].items()}
gl={n:np.array(v) for n,v in gripped['local'].items()}
start_book=gw['hand_l']@catch_mount; end_book=base['hand_l']@mount
hand_start=np.linalg.inv(catch_mount); hand_end=np.linalg.inv(mount)
# +Y is screen-right, +Z is up. Explicit projected heading chooses clockwise
# instead of allowing a shortest quaternion blend to choose the opposite route.
edge_start=start_book[:3,0]; edge_end=end_book[:3,0]
angle_start=math.atan2(edge_start[1],edge_start[2])
angle_end=math.atan2(edge_end[1],edge_end[2])
while angle_end<angle_start: angle_end+=2*math.pi
depth_start=math.asin(edge_start[0]); depth_end=math.asin(edge_end[0])
def book_recovery(u):
    turn=ease(0.,.90,u); lower=ease(.12,1.,u)
    angle=(1-turn)*angle_start+turn*angle_end
    depth=(1-turn)*depth_start+turn*depth_end
    edge=np.array([math.sin(depth),math.cos(depth)*math.sin(angle),math.cos(depth)*math.cos(angle)])
    normal=(1-turn)*start_book[:3,2]+turn*end_book[:3,2]
    position=(1-lower)*start_book[:3,3]+lower*end_book[:3,3]
    position+=np.array([0.,2.0,-.55])*math.sin(math.pi*lower)**2
    return mat(frame(edge,normal),position)

times=[i/192 for i in range(193)]; poses=[]; book_keys=[]
for t in times:
    age=t*duration
    if age<=grip_end:
        pose=landing_pose(age); poses.append(pose)
        book_keys.append(np.array(pose['component']['hand_l'])@catch_mount)
        continue
    u=np.clip((age-grip_end)/settle_seconds,0.,1.); recover=ease(0.,1.,u)
    target_book=book_recovery(u)
    hand=target_book@blend(hand_start,hand_end,recover)
    h=hand[:3,:3]; wrist=hand[:3,3]
    shoulder=(1-recover)*gw['upperarm_l'][:3,3]+recover*base['upperarm_l'][:3,3]
    deform=h@rest['hand_l'][:3,:3].T
    axis=unit(wrist-shoulder); reach=np.linalg.norm(wrist-shoulder)
    along=(lu*lu-ll*ll+reach*reach)/(2*reach); circle=shoulder+axis*along
    # Carry the elbow with the complete forearm, retaining the neutral wrist.
    # This is the native idle solver's pole, not V10's fixed-elbow wrist roll.
    source_elbow=(1-recover)*gw['lowerarm_l'][:3,3]+recover*base['lowerarm_l'][:3,3]
    pole=.82*(wrist-deform@rl)+.18*source_elbow
    bend=unit(pole-circle-axis*np.dot(pole-circle,axis))
    elbow=circle+bend*math.sqrt(max(0.,lu*lu-along*along))
    lower=frame(wrist-elbow,deform@dorsal)@frame(rl,dorsal).T
    upper=swing(lower@ru,elbow-shoulder)@lower
    world={n:m.copy() for n,m in rest.items()}
    world['upperarm_l']=mat(upper@rest['upperarm_l'][:3,:3],shoulder)
    world['lowerarm_l']=mat(lower@rest['lowerarm_l'][:3,:3],elbow); world['hand_l']=hand
    world['clavicle_l']=blend(gw['clavicle_l'],base['clavicle_l'],recover)
    world['clavicle_l'][:3,3]=shoulder-world['clavicle_l'][:3,:3]@local['upperarm_l'][:3,3]
    for n in names:
        if n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'): continue
        part=local[n].copy() if 'twist_' in n else blend(gl[n],base_local[n],recover)
        world[n]=world[parent[n]]@part
    result={'local':{},'component':{}}
    entry=1-ease(0.,.15,u); settle=ease(.82,1.,u)
    for n in names:
        part=np.linalg.inv(world[parent[n]])@world[n]
        if n in ('upperarm_l','lowerarm_l','hand_l'):
            part=blend(part,gl[n],entry); part=blend(part,base_local[n],settle)
        result['local'][n]=part.tolist()
    rebuilt={n:m.copy() for n,m in rest.items()}
    for n in names:
        rebuilt[n]=rebuilt[parent[n]]@np.array(result['local'][n])
        result['component'][n]=rebuilt[n].tolist()
    poses.append(result); book_keys.append(target_book)
poses[0]=focus['poses'][-1]; poses[-1]=grip['poses'][0]
# Contact and arm use the same baked clock; no per-frame IK or skin fitting.
mount_keys=[(np.linalg.inv(np.array(pose['component']['hand_l']))@book).tolist() for pose,book in zip(poses,book_keys)]
mount_keys[0]=catch_mount.tolist(); mount_keys[-1]=mount.tolist()
data={k:v for k,v in landing.items() if k not in ('times','poses','seconds','revision')}
data.update({'revision':11,'times':times,'arm_order':names,'poses':poses,
    'seconds':{'close':close,'palm_prepare':prepare,'drop':drop,'contact_hold':hold,'grip':grip_seconds,'settle':settle_seconds,'total':duration},
    'grip_contact':contact/duration,'book_in_hand':mount.tolist(),'catch_book_in_hand':catch_mount.tolist(),
    'return_mounts':mount_keys,'roll_mid_seconds':grip_end+.55*settle_seconds,
    'recovery_reference':{'correction':'after landing rotate to screen-right clockwise, then settle to idle',
        'landing_baseline':'VideoRecovery20261010/landing-baseline-v9.json',
        'video':'dae0d3b6859f77d7273cb211991421f5.mp4'},
    'screen_clockwise_foreedge_degrees':[math.degrees(angle_start),math.degrees(angle_end)],
    'intent':'preserve V9 landing; clockwise book-led recovery; elbow supports wrist; no additive wrist roll',
    'runtime_tested':False,'rendered':False})
(P/'return.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
def vec(v): return ','.join(f'{x:.10f}' for x in v)
header=['#pragma once','#include "SpellbookAuthoredGrip.h"','// Generated by Focus/author_return.py; V11 clockwise recovery.',
    'namespace SpellbookAuthoredSpineDownReturn {',f'inline constexpr int32 KeyCount={len(times)};',
    '// POD constants avoid oversized dynamic initializers under Live Coding.',
    'struct FKeyBone { double Rotation[4]; double Position[3]; };',
    'inline constexpr FKeyBone Poses[KeyCount][SpellbookAuthoredGrip::BoneCount]={']
for pose in poses:
    header.append('{')
    for n in names:
        m=np.array(pose['local'][n]); header.append(f'    {{{{{vec(R.from_matrix(m[:3,:3]).as_quat())}}},{{{vec(m[:3,3])}}}}},')
    header.append('},')
header+=['};','}']
(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredReturn.h').write_text('\n'.join(header)+'\n',encoding='utf-8')
header=['#pragma once','#include "SpellbookAuthoredGrip.h"','#include "SpellbookFocusMotion.h"',
    '// Generated with the arm keys; one clockwise book/contact path.',
    'namespace SpellbookReturnContact {','struct FMountKey { double Rotation[4]; double Position[3]; };',
    f'inline constexpr int32 KeyCount={len(times)};','inline constexpr FMountKey Keys[KeyCount]={']
for m in map(np.array,mount_keys):
    header.append(f'    {{{{{vec(R.from_matrix(m[:3,:3]).as_quat())}}},{{{vec(m[:3,3])}}}}},')
header+=['};','inline FTransform Key(int32 I) {','    const auto& K=Keys[I];',
    '    return FTransform(FQuat(K.Rotation[0],K.Rotation[1],K.Rotation[2],K.Rotation[3]).GetNormalized(),',
    '        FVector(K.Position[0],K.Position[1],K.Position[2]));','}',
    'inline FTransform Mount(float Age) {',
    '    const float Sample=FMath::Clamp(Age/SpellbookFocusMotion::ReturnLength,0.f,1.f)*(KeyCount-1);',
    '    const int32 A=FMath::Min(FMath::FloorToInt(Sample),KeyCount-2);',
    '    FTransform Result; Result.Blend(Key(A),Key(A+1),Sample-A); return Result;','}','}']
(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookReturnContact.h').write_text('\n'.join(header)+'\n',encoding='utf-8')
print(f'Saved V11 {len(times)} arm/contact keys: {duration:.2f}s; clockwise fore-edge {math.degrees(angle_end-angle_start):.1f} degrees.')
