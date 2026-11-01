"""Requested reload hand review only; no editor or gameplay acceptance."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'reload_library','exec'))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((O/'final_poses.json').read_text()).items()}
digits={f'{finger}_{j:02d}_l' for finger in ('index','middle','ring','pinky','thumb') for j in (1,2,3)}
report={'source_review_only':True,'max_unowned_matrix_delta':0.,'max_local_translation_delta_mm':0.,'max_local_scale_delta':0.,'timings':{}}
for role,rows in final.items():
 for f,row in enumerate(rows):
  old=clips[role][f]
  report['max_unowned_matrix_delta']=max(report['max_unowned_matrix_delta'],max(max(abs(row[n][i][j]-old[n][i][j]) for i in range(4) for j in range(4)) for n in names if n not in digits))
  for n in digits:
   a=row[parents[n]].inverted()@row[n];b=old[parents[n]].inverted()@old[n]
   report['max_local_translation_delta_mm']=max(report['max_local_translation_delta_mm'],(a.translation-b.translation).length*1000)
   report['max_local_scale_delta']=max(report['max_local_scale_delta'],(a.to_scale()-b.to_scale()).length)
def clock(t,end):
 src=[0,8,18,26,32,38,42,50,54];paced=[0,8,24,38,44,54,62,74,78]
 if t>=78:return min(end,t-24)
 i=max(0,min(7,bisect.bisect_right(paced,t)-1));span=paced[i+1]-paced[i];w=(t-paced[i])/span
 def slope(k):
  if k in (0,8):return 1
  a=(src[k]-src[k-1])/(paced[k]-paced[k-1]);b=(src[k+1]-src[k])/(paced[k+1]-paced[k]);return 2*a*b/(a+b)
 return (2*w**3-3*w*w+1)*src[i]+(w**3-2*w*w+w)*span*slope(i)+(-2*w**3+3*w*w)*src[i+1]+(w**3-w*w)*span*slope(i+1)
def sampled(rows,t):
 i=min(int(t),len(rows)-2);w=t-i;a,b=rows[i:i+2];out={}
 for n in names:
  x=a[parents[n]].inverted()@a[n] if parents[n] else a[n]
  y=b[parents[n]].inverted()@b[n] if parents[n] else b[n]
  p,q,sc=x.decompose();pp,qq,ss=y.decompose();m=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
  out[n]=out[parents[n]]@m if parents[n] else m
 return out
setup_render();s.render.resolution_x=720;s.render.resolution_y=480
folder=O/'MotionReview';folder.mkdir(exist_ok=True)
for role in ('reload','reload_empty_mag10'):
 rows=final[role];end=len(rows)-1;duration=(end+24)/30;report['timings'][role]=duration
 # Both a close-up and a fixed authoring side view expose contact and arm motion.
 target=(rows[24]['hand_l'].translation+rows[24]['middle_02_l'].translation)*.5
 for k in range(round(duration*15)+1):
  row=sampled(rows,clock(k*2,end));set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
  ext=bpy.data.objects.get('M24_Magazine10');extended=role.endswith('mag10');bpy.data.objects['M24_clip'].hide_render=extended
  if ext:ext.hide_render=not extended;ext.matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  cam.location=target+Vector((.40,-.16,.15));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.70
  s.render.filepath=str(folder/f'{role}_{k:03d}.png');bpy.ops.render.render(write_still=True)
(O/'source_review.json').write_text(json.dumps(report,indent=2));print('M24_RELOAD_MOTION_REVIEW_RENDERED',json.dumps(report),flush=True)
