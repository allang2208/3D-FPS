import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;out={}
for w in ['m4','akm']:
 for v in ['vertical']:
  title=v.title() if w=='m4' else v;name=f'A_{w.upper()}_{title}_idle.blend';rows={}
  for label,path in [('before',O.parent/('VerticalGripErgonomic20260911' if w=='m4' else 'CantedGripMigration20260911/akm')/v/name),('after',O/w/v/name)]:
   bpy.ops.wm.open_mainfile(filepath=str(path));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};fore=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized();desired=(p['hand_l'].to_3x3()@rest['hand_l'].to_3x3().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation)).normalized()
   rows[label]={'wrist_axis_bend_deg':math.degrees(fore.angle(desired)),'elbow_bend_deg':math.degrees((p['lowerarm_l'].translation-p['upperarm_l'].translation).angle(p['hand_l'].translation-p['lowerarm_l'].translation)),'finger_local_quaternions':{n:list(r.pose.bones[n].matrix_basis.to_quaternion()) for n in p if n.startswith(('index','middle','ring','pinky')) and n.endswith('_l')}}
  diffs=[]
  from mathutils import Quaternion
  for n,a in rows['before'].pop('finger_local_quaternions').items():
   b=rows['after']['finger_local_quaternions'][n];diffs.append(math.degrees(Quaternion(a).rotation_difference(Quaternion(b)).angle))
  rows['after'].pop('finger_local_quaternions');rows['four_finger_rotation_max_change_deg']=max(diffs);out[w+'/'+v]=rows
(O/'pose_quality.json').write_text(json.dumps(out,indent=2));print('FRONT_POSE_QUALITY',out,flush=True)
