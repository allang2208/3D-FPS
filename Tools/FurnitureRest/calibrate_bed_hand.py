"""Fit the resting left palm above the actual skinned torso surface."""
import sys,json
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
sys.argv=['hand-fit','--','--candidate','--all','--review',str(OUT/'HandFit'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
dom=[geo['bone_names'][max(ws,key=lambda x:x[1])[0]] for ws in geo['weights']]
def arm_branch(name):
    bone=ix[name]
    while bone>=0:
        if names[bone].startswith(('clavicle_','upperarm_')):return True
        bone=parents[bone]
    return False
mask=np.array([not arm_branch(b) for b in dom]);body_tri=tri[np.all(mask[tri],axis=1)]
ids=np.array([i for i,b in enumerate(dom) if b.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')) and b.endswith('_l')])[::3]
rows={}
previous=json.loads((OUT/'hand_fit.json').read_text()) if (OUT/'hand_fit.json').exists() else {}
for kind in sorted({k.split('.')[1] for k in rig['clips']}):
    f=np.array(rig['clips'][f'Rest.{kind}.Idle']['frames'][0]);v=skin(f);w=fk(f)
    tree=BVHTree.FromPolygons(v.tolist(),body_tri.tolist(),all_triangles=True)
    gaps=[]
    for i in ids:
        p=v[i];loc,_,_,_=tree.ray_cast(Vector(p+[0,0,100]),Vector((0,0,-1)),200)
        if loc is not None:gaps.append(float(loc.z+.25-p[2]))
    adjust=max(gaps);height=float(w[ix['hand_l'],2,3]-w[ix['pelvis'],2,3])+adjust
    rows[kind]={'wrist_height_offset_cm':height,'correction_cm':adjust}
    print('BED_HAND_FIT',kind,rows[kind],flush=True)
(OUT/'hand_fit.json').write_text(json.dumps(rows,indent=2))
