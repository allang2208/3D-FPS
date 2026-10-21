"""Repair only the three left thumb local rotations on the accepted V4 pose.

Native bind, skin weights, finger lengths, palm, arm and book mount are frozen.
Bounded thumb-only fitting keeps the tip joints from bending in opposite ways.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import least_squares
P=Path(__file__).resolve().parent;ROOT=P.parents[1];V4=P.parent/'PistolBookPoseV4_20261020'
V9=P.parent/'BareSkinV9Rollout_20261017';sys.path.insert(0,str(V9))
from jc import Driver
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def mat(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
s=read(V9/'Snapshots/01e184ddd1b7.json');payload=read(V9/'Work/batch1/01e184ddd1b7.json')
d=read(V4/'candidate.json');pose={n:np.array(m) for n,m in d['poses']['aim']['left'].items()}
names={b['index']:n for n,b in s['bones'].items()};parent={n:names.get(b['parent']) for n,b in s['bones'].items()}
rest={n:mat(R.from_quat(b['q']).as_matrix(),b['t']) for n,b in s['bones'].items()}
local={n:np.linalg.inv(rest[parent[n]])@m if parent[n] else m for n,m in rest.items()}
thumb=['thumb_01_l','thumb_02_l','thumb_03_l']
oldlocal={n:np.linalg.inv(pose[parent[n]])@pose[n] for n in thumb}
x=np.array(payload['positions']);ids=payload['vertex_ids'];idmap={v:i for i,v in enumerate(ids)}
weights=[payload['weights'].get(str(v),w) for v,w in zip(ids,s['weights'])]
shapes=dict(payload['morphs']);shapes.update(read(V9/'Work/batch1_pose4/01e184ddd1b7.json')['morphs'])
driver=Driver(s['bones'],shapes)
amounts=driver.weights({n:(m[:3,3],R.from_matrix(m[:3,:3]).as_quat()) for n,m in pose.items()})
original=x.copy()
for name,a in amounts.items():
    if a<.001 or name not in shapes:continue
    for row in shapes[name]:
        i=idmap[row[0]];x[i]+=a*(np.array(row[1:4])-original[i])
before=np.load(V4/'aim_left.npz')['X'];book=np.array(d['book_frames']['aim']);to_book=np.linalg.inv(book)
mask=np.array([sum(w.get(n,0) for n in thumb)>0. for w in weights]);ix=np.flatnonzero(mask)
wt=np.array([[weights[i].get(n,0) for n in thumb] for i in ix])
point=np.c_[x[ix],np.ones(len(ix))]
bind={n:point@np.linalg.inv(rest[n]).T for n in thumb}
old=before[ix];oldbook=old@to_book[:3,:3].T+to_book[:3,3]
tip=wt[:,2]>.65
pad=np.flatnonzero(tip & (oldbook[:,0]>.5))
pad=pad[np.argsort(np.abs(oldbook[pad,2]+2.97))[:12]]
pad_target=oldbook[pad].mean(axis=0)
rel=R.from_matrix(local[thumb[0]][:3,:3].T@oldlocal[thumb[0]][:3,:3])
q=rel.as_quat();q=q if q[3]>=0 else -q
old_twist=2*np.arctan2(q[0],q[3]);swing=rel*R.from_rotvec([-old_twist,0,0])

def evaluate(a):
    qs=[local[thumb[0]][:3,:3]@(R.from_rotvec([0,a[0],a[1]])*swing*R.from_rotvec([a[2],0,0])).as_matrix(),
        local[thumb[1]][:3,:3]@R.from_rotvec([0,0,-a[3]]).as_matrix(),
        local[thumb[2]][:3,:3]@R.from_rotvec([0,0,-a[4]]).as_matrix()]
    new={};v=old.copy()
    for j,n in enumerate(thumb):
        new[n]=(new.get(parent[n],pose[parent[n]]))@mat(qs[j],oldlocal[n][:3,3])
        v+=((bind[n]@new[n].T)[:,:3]-(bind[n]@pose[n].T)[:,:3])*wt[:,j,None]
    return new,qs,v,v@to_book[:3,:3].T+to_book[:3,3]

def residual(a):
    new,qs,v,b=evaluate(a)
    # Closest convex book bounds; only newly moving thumb skin participates.
    planes=np.stack([-b[:,0],b[:,0]-15.52,-b[:,1]-12.10,b[:,1]-12.10,-b[:,2]-2.85,b[:,2]-2.85],axis=1)
    distance=planes.max(axis=1)
    regular=(a-np.radians([0,0,10,18,8]))*np.array([4,4,1.5,1.5,2])
    return np.r_[np.minimum(distance-.04,0)*20,
        (b[pad,2]+2.97)*5,(b[pad].mean(axis=0)[:2]-pad_target[:2])*[.6,.5],
        np.maximum(.6-b[pad,0],0)*4,np.maximum(b[pad,0]-4.8,0)*2,regular]

low=np.radians([-30,-30,-8,2,2]);high=np.radians([30,30,22,45,25])
fit=least_squares(residual,np.radians([0,0,12,18,8]),bounds=(low,high),max_nfev=180,ftol=1.e-9,xtol=1.e-9,gtol=1.e-8)
new,qs,v,b=evaluate(fit.x)
final=before.copy();final[ix]=v
np.savez_compressed(P/'after.npz',X=final)
np.savez_compressed(P/'before.npz',X=before)
result={'scope':'only thumb_01_l, thumb_02_l, thumb_03_l local rotations',
    'local_rotations':{n:R.from_matrix(qs[j]).as_quat().tolist() for j,n in enumerate(thumb)},
    'local_positions':{n:oldlocal[n][:3,3].tolist() for n in thumb},
    'old_root_roll_degrees':float(np.degrees(old_twist)),
    'parameters_degrees':np.degrees(fit.x).tolist(),
    'old_pad_center_book_cm':pad_target.tolist(),'new_pad_center_book_cm':b[pad].mean(axis=0).tolist(),
    'fixed':['book','palm','other fingers','shoulder','elbow','wrist position and rotation','right arm','native bind','skin weights'],
    'cost':float(fit.cost),'runtime_integrated':False}
qr=(R.from_matrix(local[thumb[0]][:3,:3]).inv()*R.from_matrix(qs[0])).as_quat()
if qr[3]<0:qr=-qr
result['new_root_roll_degrees']=float(np.degrees(2*np.arctan2(qr[0],qr[3])))
result['non_thumb_vertices_max_change_cm']=float(np.max(np.linalg.norm(final[~mask]-before[~mask],axis=1)))
(P/'thumb_pose.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
header=['#pragma once','#include "CoreMinimal.h"',
    '// Generated by SourceAssets/PistolBookThumbV5_20261020/author_thumb.py.',
    '// Native M4 left-thumb locals only; no bone translation, scale or grip-mount edit.',
    'namespace SpellbookPistolThumbPose {',
    'inline const TCHAR* Names[]={TEXT("thumb_01_l"),TEXT("thumb_02_l"),TEXT("thumb_03_l")};',
    'inline const FQuat Rotations[]={']
for n in thumb:header.append('    FQuat('+','.join(f'{x:.12f}' for x in result['local_rotations'][n])+'),')
header+=['};','}']
(ROOT/'Source/FPSGAME/Weapons/Spellbook/SpellbookPistolThumbPose.h').write_text('\n'.join(header)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ['old_root_roll_degrees','parameters_degrees','old_pad_center_book_cm','new_pad_center_book_cm','cost']},indent=2))
