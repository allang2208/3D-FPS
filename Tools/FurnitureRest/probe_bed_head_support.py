"""Measure pillow contact on the skull separately from the neck geometry."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
sys.argv=['head-fit','--','--candidate','--all','--review',str(OUT/'HeadFit'),'--config',str(OUT/'review_config.json')]
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
reference_world=fk(ref)
print('HEAD_REFERENCE',reference_world[ix['head'],:3,3],headpoints.min(axis=0),headpoints.max(axis=0),flush=True)
skull=headpoints[(headpoints[:,2]>reference_world[ix['head'],2,3]-5)&(headpoints[:,1]<0)][::3]
lookup=json.loads((OUT/'Geometry/index.json').read_text())
for kind in ('Bed','ApartmentBed','Hospital'):
    profile=profiles[kind];slot=profile['slots'][0];scale=np.array(profile.get('scale',[1,1,1]));seat=np.array(slot['seat'])*scale;seat[2]-=config['types'][kind]['surface_height']
    angle=math.radians(slot['yaw']-90);turn=np.array(Matrix.Rotation(angle,3,'Z'))
    g=json.loads(Path(lookup[profile['mesh']]).read_text());tree=BVHTree.FromPolygons((np.array(g['positions'])*scale).tolist(),g['triangles'],all_triangles=True)
    f0=np.array(rig['clips'][f'Rest.{kind}.Idle']['frames'][0]);w0=fk(f0)
    for delta in (0,5,10,15,20):
        f=f0.copy()
        for name in ('neck_01','neck_02'):
            setrot(f,ix[name],np.array(Matrix.Rotation(math.radians(delta),3,'X'))@w0[ix[name],:3,:3])
        # Lower the occiput while letting the face rotate back with the neck.
        w=fk(f);hm=w[ix['head']]@ibind[ix['head']]
        hp=(skull@hm[:3,:3].T+hm[:3,3])@turn.T+seat;gaps=[]
        for p in hp:
            loc,_,_,_=tree.ray_cast(Vector(p)+Vector((0,0,35)),Vector((0,0,-1)),90)
            if loc is not None:gaps.append((float(p[2]-loc.z),p.tolist()))
        print('SKULL_GAP',kind,delta,min(gaps) if gaps else None,flush=True)
