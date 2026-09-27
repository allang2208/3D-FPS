import bpy,bmesh,json
from pathlib import Path
r=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(r/'UEAfter/SM_Staff_grip_lining_false_UE_After.fbx'))
o=next(o for o in bpy.context.selected_objects if o.type=='MESH')
b=bmesh.new();b.from_mesh(o.data);bmesh.ops.remove_doubles(b,verts=list(b.verts),dist=.0002)
print('BOUNDARY_LOCATIONS '+json.dumps([[list(v.co) for v in e.verts] for e in b.edges if e.is_boundary]))
