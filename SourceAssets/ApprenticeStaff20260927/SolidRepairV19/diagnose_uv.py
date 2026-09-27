import bpy,json
from pathlib import Path
r=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(r/'Staff_SolidCrystal_V19.blend'))
def show(o):
 print(o.name,[(v.name,v.active_render,v.active_clone) for v in o.data.uv_layers],o.data.uv_layers.active_index)
 print([(l.name,[list(d.uv) for d in l.data[:4]]) for l in o.data.uv_layers])
for name in ('SM_Staff_Body','SM_Staff_head_crystal_false'):show(bpy.data.objects[name])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(r/'Export/SM_Staff_Body.fbx'))
show(next(o for o in bpy.context.selected_objects if o.type=='MESH'))
