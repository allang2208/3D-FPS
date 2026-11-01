from pathlib import Path
code=(Path(__file__).parent/'review.py').read_text()
exec(compile(code.split('setup_render();s.render.resolution_x=960')[0],'runtime_review','exec'))
setup_render();s.render.resolution_x=768;s.render.resolution_y=432
folder=O/'Playback';folder.mkdir(exist_ok=True)
def progress_at(t):
 if t<=.5:return t/.5
 if t<1.7:return 1.
 if t<2.1:return max(0,1-(t-1.7)/.4)
 if t<2.35:return (t-2.1)/.5
 if t<2.55:return max(0,.5-(t-2.35)/.4)
 return 0.
for i in range(85):
 t=i/30;p=progress_at(t);row=runtime(p,(t/.63)%1)
 render(row,folder/f'frame_{i:03d}.png')
idle=component(local_pose('idle',0));details={'loop_seam':{},'exit_vs_reversed_entry':{},'finger_local_rotation_delta_degrees':0.,'finger_local_translation_delta_mm':0.,'runtime_game_tested':False,'preview_stride_period_seconds':.63}
def difference(a,b):
 position=max((a[n].translation-b[n].translation).length*1000 for n in names)
 angles=[]
 for n in names:
  q=a[n].to_quaternion().inverted()@b[n].to_quaternion();angles.append(math.degrees(min(q.angle,2*math.pi-q.angle)))
 return {'max_bone_position_mm':position,'max_bone_angle_degrees':max(angles)}
details['loop_seam']=difference(component(local_pose('sprint_loop',0)),component(local_pose('sprint_loop',1)))
for p in (0,.25,.5,.75,1):details['exit_vs_reversed_entry'][p]=difference(component(local_pose('sprint_enter',p*.5)),component(local_pose('sprint_exit',(1-p)*.4)))
for p in np.linspace(0,1,61):
 for ph in (0,.25,.5,.75):
  row=runtime(float(p),ph)
  for n in names:
   if n=='hand_l' or n=='hand_r' or not (under(n,'hand_l') or under(n,'hand_r')):continue
   a=row[parents[n]].inverted()@row[n];b=idle[parents[n]].inverted()@idle[n];q=a.to_quaternion().inverted()@b.to_quaternion()
   details['finger_local_rotation_delta_degrees']=max(details['finger_local_rotation_delta_degrees'],math.degrees(min(q.angle,2*math.pi-q.angle)))
   details['finger_local_translation_delta_mm']=max(details['finger_local_translation_delta_mm'],(a.translation-b.translation).length*1000)
(O/'transition_detail.json').write_text(json.dumps(details,indent=2));print('M24_TRANSITION_REVIEW',json.dumps(details),flush=True)
