import bpy,math,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumThrow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
def sample(name,t):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
for clip,end,hold,acquire,lock in [('reload',126,20,36,50),('reload_empty',162,16,31,43)]:
 base=sample('BeforeThrow_'+clip,0);LH=base['WPN_root'].inverted()@base['hand_l'];RH=base['WPN_root'].inverted()@base['hand_r'];left=right=contact=carry=0;depth=[];behind=None;pose_position=pose_angle=0
 target=sample('A_M4_DrumThrow_'+clip,lock);carry_relative=target['WPN_SOCKET_Magazine'].inverted()@target['hand_l']
 for k in range(end*2+1):
  t=k/2;pose=sample('A_M4_DrumThrow_'+clip,t);W=pose['WPN_root'];h=W.inverted()@pose['hand_l'];hr=W.inverted()@pose['hand_r'];right=max(right,(hr.translation-RH.translation).length*100);depth.append(pose['hand_r'].translation.y*100)
  if t<=hold:left=max(left,(h.translation-LH.translation).length*100)
  if t==acquire:behind=list(pose['hand_l'].translation)
  if acquire<=t<=lock:carry=max(carry,((pose['WPN_SOCKET_Magazine'].inverted()@pose['hand_l']).translation-carry_relative.translation).length*100)
  if t>=lock:
   old=sample('BeforeThrow_'+clip,t);contact=max(contact,((pose['WPN_SOCKET_Magazine'].inverted()@pose['hand_l']).translation-(old['WPN_SOCKET_Magazine'].inverted()@old['hand_l']).translation).length*100)
   for n in pose:
    if n.endswith('_l'):
     p=W.inverted()@pose[n];q=old['WPN_root'].inverted()@old[n]
     pose_position=max(pose_position,(p.translation-q.translation).length*100)
     angle=math.degrees(p.to_quaternion().rotation_difference(q.to_quaternion()).angle);pose_angle=max(pose_angle,min(angle,360-angle))
 report[clip]={'support_grip_drift_cm':left,'right_grip_drift_cm':right,'right_hand_depth_range_cm':max(depth)-min(depth),'acquire_position_m':behind,'carried_drum_contact_drift_cm':carry,'installation_contact_drift_cm':contact,'accepted_installation_bone_position_error_cm':pose_position,'accepted_installation_bone_angle_error_deg':pose_angle}
 assert pose_position<.001 and pose_angle<.06,report[clip]
 assert max(left,right,carry,contact,max(depth)-min(depth))<.01,report[clip]
 assert behind[0]<-.30 and behind[1]<-.25 and behind[2]<-.30,report[clip]
(O/'throw_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
