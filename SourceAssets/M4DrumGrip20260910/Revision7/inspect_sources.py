import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
for label,path,action in [('drum',O.parent/'Revision6/M4_DrumThrow_Editable.blend','A_M4_DrumThrow_reload_empty'),('standard',O.parent.parent/'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend','M4_MAT_reload_empty')]:
 bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
 for f in [0,43,54,80,88,92,97,100,105,111,115,120,125,127,130,135,143,162]:
  s.frame_set(f);bpy.context.view_layer.update();w=r.pose.bones['WPN_root'].matrix;h=w.inverted()@r.pose.bones['hand_l'].matrix
  rows.append({'frame':f,'left_in_weapon':list(h.translation),'weapon_position':list(w.translation),'weapon_angles':list(w.to_euler())})
 report[label]=rows
(O/'source_poses.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
