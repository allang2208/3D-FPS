"""Scoped source checks requested for the melee adjustment, without PIE."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
sources=json.loads((O/'sources.json').read_text());auth=json.loads((O/'authoring.json').read_text());report={}
for key,a in auth.items():
 d=sources[key];bpy.ops.wm.open_mainfile(filepath=a['blend'],use_scripts=False);r=bpy.data.objects[d['rig']];scene=bpy.context.scene
 action=bpy.data.actions[a['action']];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];r.data.pose_position='POSE'
 idle={n:Matrix(m) for n,m in d['idle'].items()};parents=d['parents'];row={'grip_mm':0.,'grip_rotation_deg':0.,'finger_local_error_mm':0.,'finger_rotation_deg':0.,'arm_length_error_mm':0.,'endpoint_mm':0.,'endpoint_rotation_deg':0.}
 for f in range(217):
  scene.frame_set(f);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones}
  for s in 'rl':
   g=p['WPN_root'].inverted()@p['hand_'+s];g0=idle['WPN_root'].inverted()@idle['hand_'+s]
   row['grip_mm']=max(row['grip_mm'],(g.translation-g0.translation).length*1000)
   row['grip_rotation_deg']=max(row['grip_rotation_deg'],math.degrees(g.to_quaternion().rotation_difference(g0.to_quaternion()).angle))
   for u,v in [('upperarm','lowerarm'),('lowerarm','hand')]:
    row['arm_length_error_mm']=max(row['arm_length_error_mm'],abs((p[v+'_'+s].translation-p[u+'_'+s].translation).length-(idle[v+'_'+s].translation-idle[u+'_'+s].translation).length)*1000)
  for n in p:
   if n.startswith(('thumb','index','middle','ring','pinky')) and parents[n]:
    g=p[parents[n]].inverted()@p[n];g0=idle[parents[n]].inverted()@idle[n]
    row['finger_local_error_mm']=max(row['finger_local_error_mm'],(g.translation-g0.translation).length*1000)
    row['finger_rotation_deg']=max(row['finger_rotation_deg'],math.degrees(g.to_quaternion().rotation_difference(g0.to_quaternion()).angle))
   if f in (0,216):
    row['endpoint_mm']=max(row['endpoint_mm'],(p[n].translation-idle[n].translation).length*1000)
    row['endpoint_rotation_deg']=max(row['endpoint_rotation_deg'],math.degrees(p[n].to_quaternion().rotation_difference(idle[n].to_quaternion()).angle))
 report[key]=row
 print('MELEE_SOURCE_CHECK',key,json.dumps(row),flush=True)
(O/'baked_source_inspection.json').write_text(json.dumps(report,indent=2))
