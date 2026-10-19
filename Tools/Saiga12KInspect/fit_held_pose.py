"""Bounded contact fitting of the real native skin against the solid handguard.

No finger translation, rest edit or mesh scaling. Metacarpals are retained;
small curl changes and a bounded palm shift open clearance around the shell.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
from pose_math import matrix,world,rotation,pack,apply,role

P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KInspect20261018'
d=json.loads((O/'Inputs/runtime-source.json').read_text())
names=[b['name'] for b in d['bones']]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']}
rest={n:matrix(d['reference'][n]) for n in names}
inverse_rest=np.array([np.linalg.inv(rest[n]) for n in names])
rest_local={n:np.linalg.inv(rest[parents[n]])@rest[n] if parents[n] else rest[n] for n in names}
idle={n:matrix(v) for n,v in d['idle'].items()}
hand={i for i,n in enumerate(names) if n=='hand_l' or n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))}
skin=[v for v in d['skin']['vertices'].values() if sum(w for b,w in v['w'] if b in hand)>.98]
indices=np.zeros((len(skin),8),dtype=int);weights=np.zeros((len(skin),8))
points=np.array([np.r_[v['p'],1.] for v in skin])
for i,v in enumerate(skin):
    for j,(b,w) in enumerate(v['w']):indices[i,j]=b;weights[i,j]=w
bounds=np.array(json.loads((O/'Inputs/contact-fit.json').read_text())['handguard_bounds_cm'])
selected=np.arange(0,len(points),3)
joints=[f'{finger}_{j:02d}_l' for finger in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
result={}
for family in ('base','angled','vertical','canted','prism'):
    held=apply(idle,role(d['profiles'][family],'idle'),0.) if family!='base' else idle
    held_world=world(held,parents);inv=np.linalg.inv(held_world['WPN_root'])
    axes={}
    for n in joints:
        delta=Rot.from_matrix(rotation(held[n])@rotation(rest_local[n]).T).as_rotvec()
        axes[n]=delta/max(np.linalg.norm(delta),1e-9) if np.linalg.norm(delta)>.05 else np.array([0.,0.,1.])
    def pose(x):
        local={n:m.copy() for n,m in held.items()}
        for i,n in enumerate(joints):local[n][:3,:3]=Rot.from_rotvec(axes[n]*np.deg2rad(x[i+3])).as_matrix()@held[n][:3,:3]
        local['thumb_01_l'][:3,:3]=Rot.from_rotvec(np.deg2rad(x[-3:])).as_matrix()@local['thumb_01_l'][:3,:3]
        w=world(local,parents)
        return local,np.array([inv@w[n]@inverse_rest[i] for i,n in enumerate(names)])
    def deform(mats,which):
        transformed=np.einsum('nkij,nj->nki',mats[indices[which]],points[which])
        return np.einsum('nki,nk->ni',transformed,weights[which])[:,:3]*100
    zero=np.zeros(3+len(joints)+3)
    _,mats0=pose(zero);initial=deform(mats0,selected)
    def error(x):
        _,mats=pose(x);p=deform(mats,selected)+x[:3]
        distance=np.minimum(p-bounds[0],bounds[1]-p).min(axis=1)
        penetration=np.maximum(distance+.08,0.)
        return np.r_[penetration*6.,(p-initial).ravel()*.016,x[:3]*.12,x[3:]*.005]
    bounds0=np.r_[[-1.5,-.6,-2.2],np.full(len(joints),-24.),np.full(3,-22.)]
    bounds1=np.r_[[1.5,.6,.3],np.full(len(joints),24.),np.full(3,22.)]
    fit=least_squares(error,zero,bounds=(bounds0,bounds1),max_nfev=100,ftol=2e-5,xtol=2e-5,gtol=2e-5)
    local,mats=pose(fit.x);p=deform(mats,np.arange(len(points)))+fit.x[:3]
    depth=np.maximum(np.minimum(p-bounds[0],bounds[1]-p).min(axis=1),0.)
    result[family]={'palm_shift_root_cm':fit.x[:3].tolist(),'joint_changes_deg':dict(zip(joints,fit.x[3:3+len(joints)].tolist())),
      'thumb_base_rotation_deg':fit.x[-3:].tolist(),'finger_local':{n:pack(local[n]).tolist() for n in joints},
      'author_fit_max_box_depth_cm':float(depth.max()),'author_fit_vertices_inside_box':int((depth>.01).sum()),'source_hand_samples':len(points)}
    print('SAIGA_HELD_CONTACT_FIT',family,'shift',fit.x[:3].round(3).tolist(),'depth',round(float(depth.max()),4),'inside',int((depth>.01).sum()),flush=True)
(O/'Inputs/held-fit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
