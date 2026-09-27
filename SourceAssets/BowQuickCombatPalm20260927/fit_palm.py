"""Place the open palm against actual upper-bow exterior; translation only."""
import json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
script=P/'author_palm.py'
ns={'__file__':str(script)}
exec(compile(script.read_text().split('\nbpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
data=ns['base']['data'];rest=ns['rest'];R=ns['R']
envelope=np.load(P.parent/'BowQuickCombatContact20260927/contact-envelope.npz')
tree=BVHTree.FromPolygons(envelope['vertices'].tolist(),envelope['faces'].tolist())
w=ns['pose'](.32);bow=w['bow_grip'];wrist=bow.inverted()@w['hand_r'].translation
skin={n:bow.inverted()@m@rest[n].inverted() for n,m in w.items()}
ids=[i for i,weights in enumerate(data['weights']) if sum(v for n,v in weights.items()
    if n=='hand_r' or (n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')))>.8]
points={i:sum((skin[n]@(R@Vector(data['positions'][i]))*v for n,v in data['weights'][i].items()),Vector()) for i in ids}
native_wrist=rest['hand_r'].translation
heel=[]
for i in ids:
    relative=R@Vector(data['positions'][i])-native_wrist
    forward=relative.dot(ns['native_f']);across=relative.dot(ns['native_a'])
    dorsal=relative.dot(ns['native_d'])
    if 2.<forward<5. and abs(across)<2. and dorsal<.4:
        heel.append((dorsal,i))
heel.sort()
if not heel:raise RuntimeError('No palmar heel vertices')
sample=[i for d,i in heel[:max(3,len(heel)//4)]]
center=sum((points[i] for i in sample),Vector())/len(sample)
shift=Vector((0.,-center.y,30.8-center.z))
gaps=[]
for i,p in points.items():
    p=p+shift
    hit,normal,index,dist=tree.ray_cast(Vector((-30.,p.y,p.z)),Vector((1,0,0)),60.)
    if hit is not None:
        gaps.append((hit.x-p.x,i,list(p)))
gaps.sort()
if not gaps:raise RuntimeError('No palm-to-riser samples')
shift.x=gaps[0][0]-.08
result={'wrist_bow_cm':list(wrist+shift),'min_surface_gap_cm':.08,
        'bearing_vertex':gaps[0][1], 'bearing_weights':data['weights'][gaps[0][1]],
        'heel_sample_vertices':sample,'target_heel_yz_cm':[0.,30.8],
        'closest_points':gaps[:8], 'fingers':'fixed anatomical open pose; no finger fit or mesh edit'}
(P/'palm-fit.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in ('wrist_bow_cm','bearing_vertex','bearing_weights')}))
