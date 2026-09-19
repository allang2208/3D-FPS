import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent/'vertical';fit=json.loads((O/'fit_final.json').read_text())
for clip in json.loads((O/'animation_build.json').read_text()):
 path=O/f'A_M4_Vertical_{clip}.blend';bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];bpy.context.view_layer.update();G=r.matrix_world@r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root'])
 for ob in bpy.context.scene.objects:
  if ob.name.startswith('VG_'):ob.matrix_world=G@Matrix(fit['attachment_local'][ob.name])
 bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('PREVIEW_ATTACHMENT_REPAIRED')
