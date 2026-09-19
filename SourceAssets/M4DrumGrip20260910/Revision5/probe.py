import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision4/M4_DrumDrop_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
for clip in ['reload','reload_empty']:
 a=bpy.data.actions['A_M4_DrumDrop_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];base=None
 for t in [0,5,14,18,26,35,50,76,100,126]:
  s.frame_set(t);bpy.context.view_layer.update();W=r.pose.bones['WPN_root'].matrix.copy()
  if base is None:base=W
  print(clip,t,'gun',list(W.translation),'delta',list((W@base.inverted()).to_euler()),'hand',list(r.pose.bones['hand_l'].head))
