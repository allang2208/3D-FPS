"""Measure the actual left side rail and compare accepted body source scale."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
I=json.loads((S/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['ASH12_Export']
T=Matrix(I['rail_frame']).inverted()@r.matrix_world.inverted()@gun.matrix_world
verts=[T@v.co for v in gun.data.vertices]
faces=[list(f.vertices) for f in gun.data.polygons if str(gun.data.materials[f.material_index].name) in ('M_ASH12_Front','M_ASH12_Upper')]
bvh=BVHTree.FromPolygons(verts,faces)
hits=[]
for x in (.28,.29,.30,.31,.32,.33,.34,.35,.36):
    row={'x_cm':100*x,'samples':[]}
    for z in (-.075,-.08,-.085,-.09,-.095):
        p,n,_,_=bvh.ray_cast(Vector((x,.1,z)),Vector((0,-1,0)),.2)
        row['samples'].append({'z_cm':z*100,'y_cm':p.y*100 if p else None})
    hits.append(row)
(O/'left_rail_geometry.json').write_text(json.dumps({'blender_sight_y_positive':'weapon left','rows':hits},indent=2))
print('LEFT_RAIL_CM',json.dumps(hits),flush=True)
