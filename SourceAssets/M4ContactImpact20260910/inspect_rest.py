import bpy
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima']
for an in ['M4_idle','M4_MAT_reload','M4_MAT_reload_empty']:
 a=bpy.data.actions[an];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 for n in ['hand_l','WPN_SOCKET_Magazine']:
  m=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones[n].matrix;print(an,n,list(m.translation),list(m.to_quaternion()))
