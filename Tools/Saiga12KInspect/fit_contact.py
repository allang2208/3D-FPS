"""Measure the native held hand against the reported 12K handguard for authoring."""
import json
from pathlib import Path
import numpy as np
import trimesh
from pose_math import matrix,world,apply,role
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KInspect20261018'
d=json.loads((O/'Inputs/runtime-source.json').read_text())
names=[b['name'] for b in d['bones']]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']}
rest={n:matrix(d['reference'][n]) for n in names}
idle={n:matrix(v) for n,v in d['idle'].items()}
g=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text())
faces=np.asarray(g['triangles'])[np.array(g['parts'])=='Handguard']
guard=trimesh.Trimesh(vertices=g['positions'],faces=faces,process=True)
guard.remove_unreferenced_vertices()
hand={i for i,n in enumerate(names) if n=='hand_l' or n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))}
skin=[v for v in d['skin']['vertices'].values() if sum(w for b,w in v['w'] if b in hand)>.98]
def positions(local):
    ws=world(local,parents);mats={n:ws[n]@np.linalg.inv(rest[n]) for n in names};inv=np.linalg.inv(ws['WPN_root'])
    return np.array([(inv@sum(w*(mats[names[b]]@np.r_[v['p'],1.]) for b,w in v['w']))[:3]*100 for v in skin])
result={'handguard_bounds_cm':guard.bounds.tolist(),'hand_samples':len(skin),'families':{}}
for family in ('base','angled','vertical','canted','prism'):
    local=apply(idle,role(d['profiles'][family],'idle'),0.) if family!='base' else idle
    p=positions(local)
    selected=((p>guard.bounds[0]-.3)&(p<guard.bounds[1]+.3)).all(axis=1)
    inside=guard.contains(p[selected]) if selected.any() else np.array([],dtype=bool)
    intersect=p[selected][inside]
    distance=trimesh.proximity.closest_point(guard,intersect)[1] if len(intersect) else np.array([])
    result['families'][family]={'inside_hand_vertices':len(intersect),'max_inside_depth_cm':float(max(distance,default=0)),'inside_bounds_cm':[intersect.min(0).tolist(),intersect.max(0).tolist()] if len(intersect) else None}
(O/'Inputs/contact-fit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
