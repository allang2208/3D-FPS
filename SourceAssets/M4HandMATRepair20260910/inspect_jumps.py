import bpy,math
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath=str(Path(__file__).parent/'M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for clip,fs in [('equip_charge',range(0,7)),('reload_empty',range(62,68))]:
 for ver in ['M4_HK416_','M4_MAT_']:
  a=bpy.data.actions[ver+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];prev={}
  for f in fs:
   s.frame_set(f);bpy.context.view_layer.update();d={}
   for n in ['WPN_root','WPN_SOCKET_Magazine','upperarm_l','lowerarm_l','hand_l']:
    b=r.pose.bones[n];q=b.matrix.to_quaternion();d[n]=[round(math.degrees(x),1) for x in b.matrix_basis.to_euler()]+[round(math.degrees(prev[n].rotation_difference(q).angle),1) if n in prev else 0]+['sc',*[round(x,2) for x in b.matrix.to_scale()],'pos',*[round(x,3) for x in b.head]];prev[n]=q
   print(ver+clip,f,d)
