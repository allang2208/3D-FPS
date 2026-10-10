"""Adapt the shared gather-palm semantics to the accepted V7 book grip."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def unit(v):return np.asarray(v)/np.linalg.norm(v)
def mat(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def frame(x,z):
    x=unit(x);z=unit(z-x*np.dot(x,z));return np.column_stack((x,np.cross(z,x),z))
def mixq(a,b,t):return Slerp([0,1],R.from_matrix([a,b]))([np.clip(t,0,1)]).as_matrix()[0]
def ease(a,b,t):
    t=np.clip((t-a)/(b-a),0,1);return t*t*t*(t*(6*t-15)+10)
def swing(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1.e-9 else R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()
grip=read(P.parent/'GripPhotoV3/grip.json')
native=read(ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json')
anatomy=read(ROOT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']['l']
cfg=read(ROOT/'Content/ColdSteelData/Skills/fireball_hand_pose.json')
bones=native['bones'];order=sorted(bones,key=lambda n:bones[n]['index']);byindex={b['index']:n for n,b in bones.items()}
parent={n:byindex.get(bones[n]['parent']) for n in order};rest={}
for n in order:
    q=np.array(bones[n]['axes']).T;q/=np.linalg.norm(q,axis=0);rest[n]=mat(R.from_matrix(q).as_matrix(),bones[n]['position'])
local={n:np.linalg.inv(rest[parent[n]])@rest[n] if parent[n] else rest[n] for n in order}
base={n:np.array(m) for n,m in grip['poses'][0]['component'].items()}
fixed={n:np.array(m) for n,m in grip['poses'][0]['local'].items()};names=grip['arm_order']
origin=rest['hand_l'][:3,3];forward=rest['middle_01_l'][:3,3]-origin
normal=unit(np.cross(rest['index_01_l'][:3,3]-origin,rest['pinky_01_l'][:3,3]-origin))
refpalm=frame(forward,normal);palm=frame(cfg['gather_forward'],cfg['gather_normal'])
goal=palm@refpalm.T@rest['hand_l'][:3,:3]
ru=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3];rl=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
lu,ll=np.linalg.norm(ru),np.linalg.norm(rl);d=np.array(anatomy['dorsal'])
times=[i/60 for i in range(40)];poses=[]
for age in times:
    u=ease(0,.65,age);opening=ease(.18,.62,age)
    wrist=(1-u)*base['hand_l'][:3,3]+u*np.array(cfg['gather_wrist'])
    shoulder=(1-u)*base['upperarm_l'][:3,3]+u*np.array(cfg['shoulder'])
    h=mixq(base['hand_l'][:3,:3],goal,ease(.16,.65,age));deform=h@rest['hand_l'][:3,:3].T
    axis=unit(wrist-shoulder);length=np.linalg.norm(wrist-shoulder)
    along=(lu*lu-ll*ll+length*length)/(2*length);circle=shoulder+axis*along
    pole=.82*(wrist-deform@rl)+.18*((1-u)*base['lowerarm_l'][:3,3]+u*np.array(cfg['elbow_pole']))
    bend=unit(pole-circle-axis*np.dot(pole-circle,axis));elbow=circle+bend*math.sqrt(max(0,lu*lu-along*along))
    lower=frame(wrist-elbow,deform@d)@frame(rl,d).T;upper=swing(lower@ru,elbow-shoulder)@lower
    world={n:m.copy() for n,m in rest.items()}
    world['upperarm_l']=mat(upper@rest['upperarm_l'][:3,:3],shoulder)
    world['lowerarm_l']=mat(lower@rest['lowerarm_l'][:3,:3],elbow);world['hand_l']=mat(h,wrist)
    world['clavicle_l']=base['clavicle_l'].copy()
    world['clavicle_l'][:3,3]=shoulder-world['clavicle_l'][:3,:3]@local['upperarm_l'][:3,3]
    handframe=h@rest['hand_l'][:3,:3].T@refpalm
    for n in names:
        if n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'):continue
        piece=fixed[n].copy();parts=n.split('_')
        if len(parts)==3 and parts[0] in cfg['digits'] and parts[1].isdigit():
            segment=int(parts[1])-1
            if segment in range(3):
                digit=cfg['digits'][parts[0]];nxt=f'{parts[0]}_{segment+2:02d}_l'
                rd=rest[nxt][:3,3]-rest[n][:3,3] if nxt in rest else rest[n][:3,:3]@rest[parent[n]][:3,:3].T@(rest[n][:3,3]-rest[parent[n]][:3,3])
                spread,flex=map(math.radians,(digit['spread'][segment],digit['gather_flex'][segment]))
                target=handframe@np.array([math.cos(flex)*math.cos(spread),math.cos(flex)*math.sin(spread),math.sin(flex)])
                rotation=frame(target,handframe[:,2])@frame(rd,normal).T@rest[n][:3,:3]
                localgoal=world[parent[n]][:3,:3].T@rotation
                piece[:3,:3]=mixq(fixed[n][:3,:3],localgoal,opening)
        world[n]=world[parent[n]]@piece
    poses.append(grip['poses'][0] if age==0 else {'local':{n:(np.linalg.inv(world[parent[n]])@world[n]).tolist() for n in names},'component':{n:world[n].tolist() for n in names}})
data={'times':times,'arm_order':names,'poses':poses,'book_in_hand':grip['book_in_hand'],
      'intent':'book leaves the unchanged spine grip, fingers open into the shared charging palm',
      'gather_source':'Content/ColdSteelData/Skills/fireball_hand_pose.json','runtime_tested':False,'rendered':False}
(P/'focus.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
def vec(v):return ','.join(f'{x:.10f}' for x in v)
header=['#pragma once','#include "SpellbookAuthoredGrip.h"','// Generated by Focus/author_focus.py; native V7, shared gather semantics.',
        'namespace SpellbookAuthoredFocus {',f'inline constexpr int32 KeyCount={len(times)};',
        'inline constexpr float Times[]={'+','.join(f'{t:.9f}f' for t in times)+'};',
        'inline const SpellbookAuthoredGrip::FArmBone Poses[KeyCount][SpellbookAuthoredGrip::BoneCount]={']
for pose in poses:
    header.append('{')
    for n in names:
        m=np.array(pose['local'][n]);header.append(f'    {{FQuat({vec(R.from_matrix(m[:3,:3]).as_quat())}),FVector({vec(m[:3,3])})}},')
    header.append('},')
header+=['};','}'];(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookAuthoredFocus.h').write_text('\n'.join(header)+'\n',encoding='utf-8')
print(f'Saved {len(times)} V7 gather frames from current book grip and shared casting-palm configuration.')
