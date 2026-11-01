from pathlib import Path
import bpy,json,numpy as np
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'M24CustomScope20261026/Donor/Source/source/arms@sniper.fbx'))
s=bpy.context.scene;s.frame_set(1);bpy.context.view_layer.update();skin=bpy.data.objects['armmesh'];ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
data={}
for g in skin.vertex_groups:
 if g.name=='R_wrist' or any(g.name.startswith('R_'+d) for d in ('thumb','point','middle','ring','pink')):
  ids=[v.index for v in skin.data.vertices if any(x.group==g.index and x.weight>.55 for x in v.groups)]
  data[g.name]=[list(ev.matrix_world@me.vertices[i].co) for i in ids]
ev.to_mesh_clear();data['bolt_matrix']=[list(x) for x in bpy.data.objects['bolt'].matrix_world]
(O/'donor_grip_surface.json').write_text(json.dumps(data));print('DONOR_GRIP_READ')
