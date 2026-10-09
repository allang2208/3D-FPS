import bpy,numpy as np,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;models=json.loads((O.parent/'Super90Foregrips20261007/models.json').read_text());mount=Matrix(models['mount_native'])
out={}
for family in ('vertical','tactical_vertical','canted','prism','angled'):
 bpy.ops.wm.read_factory_settings(use_empty=True)
 path=O/'Diagnostics'/('foregrip_'+family+'.fbx')
 if not path.exists():path=Path(models['parts'][family]['fbx'])
 bpy.ops.import_scene.fbx(filepath=str(path));verts=[];faces=[]
 for ob in bpy.data.objects:
  if ob.type=='MESH':
   off=len(verts);verts.extend([list(mount@ob.matrix_world@v.co) for v in ob.data.vertices]);ob.data.calc_loop_triangles();faces.extend([[off+i for i in t.vertices] for t in ob.data.loop_triangles])
 out[family]={'vertices':verts,'faces':faces,'source':str(path)}
(O/'Diagnostics/foregrip_geometry.json').write_text(json.dumps(out,separators=(',',':')));print('FOREGRIP_GEOMETRY',list(out),flush=True)
