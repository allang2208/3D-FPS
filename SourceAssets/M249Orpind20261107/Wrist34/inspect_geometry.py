"""Recheck the exact saved native output, including actual morphed skin surfaces."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import json,sys,pickle
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;src=r.parent/'Wrist33'
sys.path.insert(0,str(src))
from pose import matrix,metrics
g=pickle.load(open(src/'geometry.pkl','rb'));bind=matrix(g['bind']);names=g['names'];ix={n:i for i,n in enumerate(names)}
capture_root=r/'geometry' if len(sys.argv)>1 and sys.argv[1]=='final' else src/'native_final'
if capture_root==r/'geometry' and (r/'geometry_final/receipt.json').exists():capture_root=r/'geometry_final'
report={}
folders={p.name:p for p in capture_root.glob('box_*')}
if (r/'geometry_prism_final/receipt.json').exists():folders.update({p.name:p for p in (r/'geometry_prism_final').glob('box_*')})
for folder in sorted(folders.values(),key=lambda p:p.name):
    meta=json.loads((folder/'review.json').read_text());geo=json.loads((folder/'geometry.json').read_text())
    raw=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+7*meta['bone_count'])
    pose=raw[:,4:].reshape(len(raw),meta['bone_count'],7)
    world=matrix(np.concatenate([pose,np.ones((*pose.shape[:2],3))],axis=-1))
    measures=metrics(world,bind,names)
    armids=[ix[n] for n in ('upperarm_l','lowerarm_l','hand_l')]
    steps=np.linalg.norm(np.diff(pose[:,armids,:3],axis=0),axis=-1)
    dominant=np.fromfile(folder/'dominant.bin',np.uint32)
    left=np.array([n.endswith('_l') and n.startswith(('lowerarm','hand_l')) for n in geo['bones']])[dominant]
    skin_slots=[i for i,n in enumerate(geo['slots']) if n.startswith('Skin_')]
    boxes=[i for i,n in enumerate(geo['slots']) if 'Box' in n and 'Surface' in n]
    samples=[]
    for row in meta['frames']:
        stem=folder/Path(row['file']).stem
        v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3)
        f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3)
        slots=np.fromfile(stem.with_suffix('.materials'),np.uint32)
        skin=np.unique(f[np.isin(slots,skin_slots)]);skin=skin[left[skin]]
        for slot in boxes:
            if slot not in row['visible_materials']:continue
            ids=np.unique(f[slots==slot]);hull=ConvexHull(v[ids]).equations
            distance=np.max(v[skin]@hull[:,:3].T+hull[:,3],axis=1)
            samples.append(dict(source=row['source'],file=row['file'],box=geo['slots'][slot],
                min_convex_clearance_cm=float(distance.min()),skin_inside_convex_count=int((distance<-.05).sum())))
    report[folder.name]=dict(frames=len(raw),finite=bool(np.isfinite(raw).all()),
        max_wrist_swing_deg=float(measures['wrist_swing'].max()),
        max_residual_twist_deg=float(abs(measures['wrist_residual_twist']).max()),
        max_arm_frame_step_cm=float(steps.max()),max_step_source=float(raw[1+np.unravel_index(steps.argmax(),steps.shape)[0],1]),
        box_samples=samples)
(r/('geometry_review_final.json' if capture_root.parent==r else 'geometry_review.json')).write_text(json.dumps(report,indent=2))
for k,v in report.items():
    worst=min(v['box_samples'],key=lambda s:s['min_convex_clearance_cm'])
    print(k,'swing',round(v['max_wrist_swing_deg'],2),'twist',round(v['max_residual_twist_deg'],2),
          'step',round(v['max_arm_frame_step_cm'],3),'worst box',worst,flush=True)
