from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('setup_render();s.render.resolution_x=960')[0],'review','exec'))
original={k:v for k,v in ue['profiles'].items()};saved={f:json.loads((O/(f+'_saved.json')).read_text())['clips'] for f in ('base','mag10')}
report={'disk_profile_samples':0,'max_preserved_position_mm':0.,'max_preserved_angle_degrees':0.,'max_native_arm_length_error_mm':0.}
preserved=[n for n in names if not under(n,'clavicle_l') or under(n,'hand_l')]
for family,role in [('base','fire'),('mag10','fire'),('base','cycle'),('mag10','cycle'),('base','reload_empty'),('mag10','reload_empty_mag10')]:
 data=ue['clips'][role]
 for i in range((data['keys']-1)*2+1):
  t=i/60;ue['profiles']=original;before=component(local_pose(role,t,family));ue['profiles']=saved;after=component(local_pose(role,t,family))
  for n in preserved:
   report['max_preserved_position_mm']=max(report['max_preserved_position_mm'],(after[n].translation-before[n].translation).length*1000)
   q=after[n].to_quaternion().rotation_difference(before[n].to_quaternion());angle=min(q.angle,2*math.pi-q.angle);report['max_preserved_angle_degrees']=max(report['max_preserved_angle_degrees'],math.degrees(angle))
  for n,p in [('lowerarm_l','upperarm_l'),('hand_l','lowerarm_l')]:report['max_native_arm_length_error_mm']=max(report['max_native_arm_length_error_mm'],abs((after[n].translation-after[p].translation).length-(rest[n].translation-rest[p].translation).length)*1000)
  report['disk_profile_samples']+=1
(O/'saved_pose_comparison.json').write_text(json.dumps(report,indent=2));print('SAVED_POSE_COMPARE',json.dumps(report),flush=True)
if report['max_preserved_position_mm']>.05 or report['max_preserved_angle_degrees']>.1:raise RuntimeError('Saved contact drift')
