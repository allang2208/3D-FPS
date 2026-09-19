import bpy,math,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumFlow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for clip,end in [('reload',126),('reload_empty',162)]:
 for t in [0,end]:
  poses=[]
  for prefix in ['BeforeFlow_','A_M4_DrumFlow_']:
   a=bpy.data.actions[prefix+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(t);bpy.context.view_layer.update();poses.append({b.name:b.matrix.copy() for b in r.pose.bones})
  print(clip,t,{n:round(math.degrees(poses[0][n].to_quaternion().rotation_difference(poses[1][n].to_quaternion()).angle),2) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']})
