import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_equip_charge'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(18);bpy.context.view_layer.update()
inv=r.pose.bones['WPN_root'].matrix.inverted()
print('POINTS', {n:list(inv@r.pose.bones[n].head) for n in ['hand_r','WPN_ChargingHandle','index_03_r','middle_03_r','WPN_root']})
