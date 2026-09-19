import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;result={}
for key,title in [('vertical','Vertical'),('prism','Prism')]:
 report={};d=O/key
 for clip,info in json.loads((d/'animation_build.json').read_text()).items():
  name=f'A_M4_{title}_'+clip;bpy.ops.wm.open_mainfile(filepath=str(d/(name+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;new=bpy.data.actions[name]
  with bpy.data.libraries.load(str(O.parent/'VerticalGripClass20260911'/key/(name+'.blend')),link=False) as (src,dst):dst.actions=[name]
  old=dst.actions[0];points=['hand_l']+[b.name for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))];delta=0;angle=0
  def sample(a,f):
   r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();return {n:r.pose.bones[n].matrix.copy() for n in points}
  for f in range(info['frames']+1):
   a=sample(old,f);b=sample(new,f)
   for n in points:
    delta=max(delta,(a[n].translation-b[n].translation).length);q=a[n].to_quaternion().rotation_difference(b[n].to_quaternion());angle=max(angle,math.degrees(min(q.angle,abs(2*math.pi-q.angle))))
  assert delta<.0001 and angle<.1,(key,clip,delta,angle);report[clip]={'max_hand_finger_position_difference_m':delta,'max_rotation_difference_degrees':angle}
 result[key]=report
(O/'contact_preservation.json').write_text(json.dumps(result,indent=2));print('CONTACT_PRESERVATION_PASS')
