import bpy,math,json
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumFlow_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;report={}
def sample(name,t):
 a=bpy.data.actions[name];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
for clip,end,hold,lock in [('reload',126,22,50),('reload_empty',162,18,35)]:
 base=sample('BeforeFlow_'+clip,0);LH=base['WPN_root'].inverted()@base['hand_l'];RH=base['WPN_root'].inverted()@base['hand_r'];left=right=rot=contact=arm=armrot=0;steps=[];previous=None
 for k in range(end*2+1):
  t=k/2;pose=sample('A_M4_DrumFlow_'+clip,t);W=pose['WPN_root'];h=W.inverted()@pose['hand_l'];hr=W.inverted()@pose['hand_r'];right=max(right,(hr.translation-RH.translation).length*100)
  if t<=hold:left=max(left,(h.translation-LH.translation).length*100);rot=max(rot,math.degrees(h.to_quaternion().rotation_difference(LH.to_quaternion()).angle))
  if t<=hold:
   for n in ['upperarm_l','lowerarm_l']:
    x=W.inverted()@pose[n];y=base['WPN_root'].inverted()@base[n];arm=max(arm,(x.translation-y.translation).length*100);a=math.degrees(x.to_quaternion().rotation_difference(y.to_quaternion()).angle);armrot=max(armrot,min(a,360-a))
  if t>=lock:
   old=sample('BeforeFlow_'+clip,t);contact=max(contact,((pose['WPN_SOCKET_Magazine'].inverted()@pose['hand_l']).translation-(old['WPN_SOCKET_Magazine'].inverted()@old['hand_l']).translation).length*100)
  if previous is not None:angle=math.degrees(previous.rotation_difference(W.to_quaternion()).angle);steps.append((t,min(angle,360-angle)))
  previous=W.to_quaternion()
 # The former static midsection now contains deliberate continuous weapon movement.
 active=[a for t,a in steps if lock<t<min(end-25,90)]
 report[clip]={'left_support_drift_before_release_cm':left,'left_support_rotation_deg':rot,'whole_left_arm_hold_drift_cm':arm,'whole_left_arm_hold_rotation_deg':armrot,'right_weapon_grip_drift_cm':right,'insert_contact_drift_cm':contact,'midsection_rotation_total_deg':sum(active),'max_half_frame_weapon_rotation_deg':max(a for t,a in steps)}
 assert left<.01 and right<.01 and rot<.05 and contact<.01 and arm<.01 and armrot<.05,report[clip]
 assert sum(active)>1,report[clip]
(O/'gesture_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
