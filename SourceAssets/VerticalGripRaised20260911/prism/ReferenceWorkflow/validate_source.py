import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
for clip,info in json.loads((O/'animation_build.json').read_text()).items():
 bpy.ops.wm.open_mainfile(filepath=str(O/('A_M4_Foregrip_'+clip+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;new=bpy.data.actions['A_M4_Foregrip_'+clip]
 with bpy.data.libraries.load(info['source'],link=False) as (src,dst):dst.actions=[info['action']]
 old=dst.actions[0]
 def sample(a,f):
  r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();return ({b.name:b.matrix.copy() for b in r.pose.bones},{b.name:b.matrix_basis.copy() for b in r.pose.bones})
 lengths=scale=translations=nonleft=contacts=0
 for f in range(info['frames']+1):
  A,a=sample(old,f);B,b=sample(new,f)
  for n in a:
   scale=max(scale,(a[n].to_scale()-b[n].to_scale()).length)
   if n.startswith(('index','middle','ring','pinky','thumb')):translations=max(translations,(a[n].translation-b[n].translation).length)
   if not n.endswith('_l'):nonleft=max(nonleft,(A[n].translation-B[n].translation).length)
  for x,y in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:lengths=max(lengths,abs((A[y].translation-A[x].translation).length-(B[y].translation-B[x].translation).length))
  interval=info.get('unchanged_contact_interval_frames')
  if interval and interval[0]<=f<=interval[1]:
   for n in ['hand_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:contacts=max(contacts,(A[n].translation-B[n].translation).length)
 report[clip]={'max_arm_length_change_m':lengths,'max_bone_scale_change':scale,'max_finger_local_translation_change_m':translations,'nonleft_position_change_m':nonleft,'preserved_contact_position_change_m':contacts}
 assert max(lengths,scale,translations,nonleft,contacts)<.0001,(clip,report[clip])
 (O/'source_validation.json').write_text(json.dumps(report,indent=2))
print('FOREGRIP_SOURCE_VALIDATION_PASS')
