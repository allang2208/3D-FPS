"""Measure the feet-to-seat handover on the actual skinned body and bed mesh."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path('D:/FPS3D/FPSGAME');BASE=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBedSideHands20261024'
OUT=BASE.parent/'MeshyBedSupportedHands20261024'
sys.argv=['fit','--','--candidate','--all','--review',str(BASE/'SupportFit'),'--config',str(BASE/'review_config.json')]
code=(ROOT/'Tools/FurnitureRest/render_review.py').read_text();exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
groot=BASE.parent/'RefineV2/Geometry';lookup=json.loads((groot/'index.json').read_text())
bed=json.loads((groot/lookup[profiles['Bed']['mesh']]).read_text());bvh=BVHTree.FromPolygons(bed['positions'],bed['triangles'],all_triangles=True)
dominant=[geo['bone_names'][max(ws,key=lambda p:p[1])[0]] for ws in geo['weights']]
pelvis=fk(ref)[ix['pelvis'],:3,3]
seat=np.array([i for i,n in enumerate(dominant) if (n=='pelvis' or n.startswith('thigh')) and np.linalg.norm(points[i]-pelvis)<25])
feet=np.array([i for i,n in enumerate(dominant) if n.startswith(('foot_','ball_'))])
samples=[]
for j,f in enumerate(np.asarray(rig['clips']['Rest.Bed.Enter']['frames'])):
    t=j/30
    if t>4.8:break
    v=skin(f);floor=float(v[feet,2].min());gaps=[]
    for p in v[seat]:
        hit,_,_,_=bvh.ray_cast(Vector(p)+Vector((0,0,30)),Vector((0,0,-1)),120)
        if hit is not None:gaps.append(float(p[2]-hit.z))
    gap=min(gaps) if gaps else 1000.
    raw=max(0.,min(floor,gap)-.45)
    fade=np.clip((t-4.45)/.35,0,1);fade=fade**3*(fade*(fade*6-15)+10)
    samples.append({'time':t,'feet_gap_cm':floor,'seat_gap_cm':gap,'root_drop_cm':raw*(1-fade)})
(OUT/'seated_support.json').write_text(json.dumps(samples,indent=2))
print('SEATED_SUPPORT',max(s['root_drop_cm'] for s in samples),flush=True)
