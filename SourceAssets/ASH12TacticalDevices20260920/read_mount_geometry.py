"""Read the source handguard surface for the new right-side accessory saddle."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
I=json.loads((S/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['ASH12_Export']
T=Matrix(I['rail_frame']).inverted()@r.matrix_world.inverted()@gun.matrix_world
vertices=[T@v.co for v in gun.data.vertices]
faces=[list(f.vertices) for f in gun.data.polygons if str(gun.data.materials[f.material_index].name) in ('M_ASH12_Front','M_ASH12_Upper')]
surface=BVHTree.FromPolygons(vertices,faces)
hits=[]
for x in (.23,.25,.27,.29,.31,.33,.35,.37):
 for z in (-.08,-.09,-.10,-.11,-.12,-.13):
  p,n,_,_=surface.ray_cast(Vector((x,-.10,z)),Vector((0,1,0)),.2)
  hits.append({'x':x,'z':z,'right_y':p.y if p else None,'normal':list(n) if n else None})
(O/'mount_geometry.json').write_text(json.dumps({'source':str(S/'ASH12Surface20260919/ASH12_Surface_Editable.blend'),'sight_frame':I['rail_frame'],'surface_samples':hits},indent=2))
print('ASH_RIGHT_HANDGUARD',json.dumps(hits),flush=True)
