import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest=r.data.bones;report={}
names=['hand_l','WPN_SOCKET_Magazine','hand_r']+[b.name for b in rest if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))]
for clip,end,lo,hi in [('reload',126,23,95),('reload_empty',162,15,80)]:
 data={}
 for label,prefix in [('before','BeforeWrist_'),('after','A_M4_DrumGrip_')]:
  a=bpy.data.actions[prefix+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];rows=[]
  for k in range(end*2+1):
   s.frame_set(k//2,subframe=(k%2)/2);bpy.context.view_layer.update();p=r.pose.bones
   cuff=p['lowerarm_twist_01_l'].matrix.to_quaternion()@rest['lowerarm_twist_01_l'].matrix_local.to_quaternion().inverted()@rest['hand_l'].matrix_local.to_quaternion();angle=math.degrees(cuff.rotation_difference(p['hand_l'].matrix.to_quaternion()).angle);angle=min(angle,360-angle)
   rows.append({'frame':k/2,'cuff_angle':angle,'poses':{n:p[n].matrix.copy() for n in names}})
  data[label]=rows
 drift=rot=0
 for a,b in zip(data['before'],data['after']):
  for n in names:
   drift=max(drift,(a['poses'][n].translation-b['poses'][n].translation).length*100);q=math.degrees(a['poses'][n].to_quaternion().rotation_difference(b['poses'][n].to_quaternion()).angle);rot=max(rot,min(q,360-q))
 report[clip]={'contact_position_drift_cm':drift,'contact_rotation_drift_deg':rot,'cuff_before_grip_max':max(x['cuff_angle'] for x in data['before'] if lo<=x['frame']<=hi),'cuff_after_grip_max':max(x['cuff_angle'] for x in data['after'] if lo<=x['frame']<=hi)}
 assert drift<.02 and rot<.1,(clip,drift,rot)
(O/'wrist_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
