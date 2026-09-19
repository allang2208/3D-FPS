import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;report={}
for clip,info in json.loads((O/'animation_build.json').read_text()).items():
 name='A_M4_Vertical_'+clip;bpy.ops.wm.open_mainfile(filepath=str(O/(name+'.blend')));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;new=bpy.data.actions[name]
 with bpy.data.libraries.load(str(O.parent/'Compact75'/(name+'.blend')),link=False) as (src,dst):dst.actions=[name]
 old=dst.actions[0];points=['hand_l']+[b.name for b in r.pose.bones if b.name.startswith(('index','middle','ring','pinky','thumb')) and b.name.endswith('_l')]
 def sample(a,f):
  r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f);bpy.context.view_layer.update();l=r.pose.bones['lowerarm_l'];h=r.pose.bones['hand_l'];u=r.pose.bones['upperarm_l'];rest=r.data.bones
  v=(h.head-l.head).normalized();desired=h.matrix.to_3x3()@rest['hand_l'].matrix_local.to_3x3().inverted()@(rest['hand_l'].head_local-rest['lowerarm_l'].head_local).normalized()
  return {n:r.pose.bones[n].matrix.copy() for n in points+['upperarm_l','lowerarm_l']},math.degrees(v.angle(desired)),math.degrees((l.head-u.head).normalized().angle(v))
 delta=0;rotation=0;angles={}
 for frame in range(info['frames']+1):
  A,oldw,olde=sample(old,frame);B,neww,newe=sample(new,frame);delta=max(delta,max((A[n].translation-B[n].translation).length for n in points))
  for n in points:
   angle=A[n].to_quaternion().rotation_difference(B[n].to_quaternion()).angle;rotation=max(rotation,math.degrees(min(angle,abs(2*math.pi-angle))))
  if frame in [0,info['frames']]:angles[str(frame)]={'shoulder_delta_from_compact_m':list(B['upperarm_l'].translation-A['upperarm_l'].translation),'old_wrist_axis_bend_deg':oldw,'new_wrist_axis_bend_deg':neww,'old_elbow_bend_deg':olde,'new_elbow_bend_deg':newe}
 assert delta<.0001 and rotation<.1,(clip,delta,rotation)
 report[clip]={'max_hand_finger_position_delta_m':delta,'max_hand_finger_rotation_delta_deg':rotation,'angles':angles};(O/'arm_validation.json').write_text(json.dumps(report,indent=2))
print('ARM_GRASP_PRESERVED_PASS')



