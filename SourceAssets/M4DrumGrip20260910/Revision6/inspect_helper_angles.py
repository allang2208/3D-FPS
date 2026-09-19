import bpy,math,json
from mathutils import Vector
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];rest=r.data.bones
a=bpy.data.actions['BeforeThrow_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
for t in [0,20,22,30,35,40,45,50]:
 s.frame_set(t);bpy.context.view_layer.update();lower=r.pose.bones['lowerarm_l'].matrix;hand=r.pose.bones['hand_l'].matrix;axis=(hand.translation-lower.translation).normalized();row={}
 for n in ['lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']:
  B=lower@rest['lowerarm_l'].matrix_local.inverted()@rest[n].matrix_local;q=r.pose.bones[n].matrix.to_quaternion()@B.to_quaternion().inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w);row[n]=math.degrees((twist+math.pi)%(2*math.pi)-math.pi)
 print(t,row)
