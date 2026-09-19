import bpy,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M4_MAT_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
for f in [34,35,35.5,36,36.5,37,37.5,38]:
 bpy.context.scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();print(f,list((r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@r.pose.bones['hand_l'].matrix).translation),flush=True)
