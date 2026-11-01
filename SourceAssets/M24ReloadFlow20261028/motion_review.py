"""Scoped reload continuity review and authoring preview at the runtime source clock."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'library','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
final={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in json.loads((O/'final_poses.json').read_text()).items()}
code=ast.parse((O/'author_flow.py').read_text())
for name in ('pose','hermite'):
 exec(compile(ast.unparse(next(n for n in code.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
source_frames=[0,8,18,21,24,27,30,34,38,40,44,50,54];paced_frames=[0,8,24,34,43,54,64,77,90,96,104,116,120]
def source_at(seconds):
 t=seconds*30
 if t>=120:return t-66
 i=max(0,min(len(paced_frames)-2,bisect.bisect_right(paced_frames,t)-1))
 def slope(k):
  if k==0 or k==len(source_frames)-1:return 1.
  a=(source_frames[k]-source_frames[k-1])/(paced_frames[k]-paced_frames[k-1]);b=(source_frames[k+1]-source_frames[k])/(paced_frames[k+1]-paced_frames[k]);return 2*a*b/(a+b)
 d=paced_frames[i+1]-paced_frames[i];return hermite(source_frames[i],source_frames[i+1],slope(i),slope(i+1),(t-paced_frames[i])/d,d)
def interpolated(role,f):
 rows=final[role];i=max(0,min(len(rows)-2,int(f*4)));w=max(0,min(1,f*4-i));a=rows[i];b=rows[i+1];out={}
 for n in names:
  aa=a[parents[n]].inverted()@a[n] if parents[n] else a[n];bb=b[parents[n]].inverted()@b[n] if parents[n] else b[n]
  p,q,sc=aa.decompose();pp,qq,ss=bb.decompose();loc=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w));out[n]=out[parents[n]]@loc if parents[n] else loc
 return out
metrics={}
for role,rows in final.items():
 original=[pose(role,k/4)[0] for k in range(len(rows))];max_local=0.;max_scale=0.;max_other=0.;max_contact=0.
 for k,row in enumerate(rows):
  for n in names:
   loc=row[parents[n]].inverted()@row[n] if parents[n] else row[n];old=original[k][parents[n]].inverted()@original[k][n] if parents[n] else original[k][n]
   if n in ('upperarm_l','lowerarm_l','hand_l') or (n.endswith('_l') and any(n.startswith(d+'_') for d in ('index','middle','ring','pinky','thumb'))):
    max_local=max(max_local,(loc.translation-old.translation).length*1000);max_scale=max(max_scale,(loc.to_scale()-old.to_scale()).length)
   if not under(n,'clavicle_l') and not under(n,'WPN_Magazine'):max_other=max(max_other,max(abs(row[n][a][b]-original[k][n][a][b]) for a in range(4) for b in range(4)))
  if 21<=k/4<=24:
   anchor=rows[88]['WPN_Magazine'].inverted()@rows[88]['hand_l'];g=row['WPN_Magazine'].inverted()@row['hand_l'];max_contact=max(max_contact,(g.translation-anchor.translation).length*1000)
 speeds=[];before=[]
 for i in range(40,55):
  t=i/30;row=interpolated(role,source_at(t));nxt=interpolated(role,source_at(t+1/30));a=pose(role,source_at(t))[0];b=pose(role,source_at(t+1/30))[0]
  # Gun-relative motion isolates the artificial hold from whole-gun presentation sway.
  x=(row['WPN_root'].inverted()@row['hand_l']).translation;y=(nxt['WPN_root'].inverted()@nxt['hand_l']).translation
  xx=(a['WPN_root'].inverted()@a['hand_l']).translation;yy=(b['WPN_root'].inverted()@b['hand_l']).translation
  speeds.append((y-x).length*3000);before.append((yy-xx).length*3000)
 metrics[role]={'max_local_bone_translation_change_mm':max_local,'max_local_scale_change':max_scale,'unrelated_component_matrix_change':max_other,'held_grip_translation_variation_mm':max_contact,'release_hand_speed_cm_s':speeds,'previous_release_hand_speed_cm_s':before}
(O/'motion_review.json').write_text(json.dumps(metrics,indent=2))
setup_render();s.render.resolution_x=640;s.render.resolution_y=360
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
node=next(n for n in ast.parse((O.parent/'M24LeftElbowReview20261028/surface_scan.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='morphs_full');exec(compile(ast.unparse(node),'morphs','exec'))
view=Matrix(((0,.01,0,0),(.01,0,0,0),(0,0,.01,0),(0,0,0,1)))@C
for n in ('M24_silencer','M24_ExtraScope_Lowpoly','M24_Laser_Lowpoly','M24_LaserHolder_Lowpoly','M24_bullet'):bpy.data.objects[n].hide_render=True
base=bpy.data.objects['M24_clip'];ext=bpy.data.objects['M24_Magazine10'];folder=O/'PreviewFrames';folder.mkdir(exist_ok=True)
for role in ('reload','reload_mag10'):
 for i in range(127):
  row=interpolated(role,source_at(i/30));r.matrix_world=Matrix.Identity(4);set_pose(row);morphs_full();r.matrix_world=view
  extended=role.endswith('_mag10');base.hide_render=extended;ext.hide_render=not extended;ext.matrix_world=view@row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP';s.render.filepath=str(folder/(role+f'_{i:03d}.png'));bpy.ops.render.render(write_still=True)
print('M24_FLOW_CONTINUITY_AND_PREVIEW_COMPLETE',flush=True)
