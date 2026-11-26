"""Check the authored neckline against unchanged native head reference meshes."""
import json,hashlib
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'SetFitReview20261115'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
rows=[]
for rig in ['Jason','Kaitlin']:
    h=read(S/'HelmetHairFitR1/Inputs'/f'{rig}_Head.json');disk=P/'Content'/(h['source'].split('.')[0].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(disk.read_bytes()).hexdigest()
    if sha!=h['sha256']:raise RuntimeError('Native head changed: '+rig)
    d=read(S/'CombatShirtR3/Authored'/f'shirt_cloth_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);outer=f[(f<len(p)//2).all(1)]
    a=BVHTree.FromPolygons(h['positions'],h['triangles'],all_triangles=True);b=BVHTree.FromPolygons(p.tolist(),outer.tolist(),all_triangles=True);pairs=a.overlap(b)
    rows.append(dict(rig=rig,head=h['source'],head_package_sha256=sha,outer_shirt_head_triangle_intersections=len(pairs),reference_pose_only=True));print('NECK_REVIEW',rig,len(pairs),flush=True)
(R/'neck-review.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
