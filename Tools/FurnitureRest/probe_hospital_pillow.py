"""Measure a small cervical adjustment while keeping the head's orientation."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
sys.argv=['pillow','--','--candidate','--all','--review',str(OUT/'PillowProbe'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
profile=profiles['Hospital'];slot=profile['slots'][0];scale=np.array(profile.get('scale',[1,1,1]));seat=np.array(slot['seat'])*scale;seat[2]-=config['types']['Hospital']['surface_height']
angle=math.radians(slot['yaw']-90);turn=np.array(Matrix.Rotation(angle,3,'Z'))
lookup=json.loads((OUT/'Geometry/index.json').read_text());g=json.loads(Path(lookup[profile['mesh']]).read_text())
tree=BVHTree.FromPolygons((np.array(g['positions'])*scale).tolist(),g['triangles'],all_triangles=True)
f0=np.array(rig['clips']['Rest.Hospital.Idle']['frames'][0]);w0=fk(f0)
for delta in (0,3,6,8,9,10):
    f=f0.copy()
    for name in ('neck_01','neck_02'):
        setrot(f,ix[name],np.array(Matrix.Rotation(math.radians(delta),3,'X'))@w0[ix[name],:3,:3])
    setrot(f,ix['head'],w0[ix['head'],:3,:3]);w=fk(f);hm=w[ix['head']]@ibind[ix['head']]
    hp=(headpoints[::8]@hm[:3,:3].T+hm[:3,3])@turn.T+seat;gaps=[]
    for p in hp:
        loc,_,_,_=tree.ray_cast(Vector(p)+Vector((0,0,25)),Vector((0,0,-1)),60)
        if loc is not None:gaps.append(float(p[2]-loc.z))
    print('HOSPITAL_PILLOW',delta,min(gaps),flush=True)
