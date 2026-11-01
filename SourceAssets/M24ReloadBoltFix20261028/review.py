from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text(),'review_library','exec'))
import sys
phase=next((x.split('=')[1] for x in sys.argv if x.startswith('stage=')),'current')
fps=120
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
cache={}
def local_pose(role,t,family='base'):
 data=ue['clips'][role];t=max(0,min(t,(data['keys']-1)/data['fps']));f=t*data['fps'];i=min(int(f),max(0,data['keys']-2));w=f-i
 layer=next(c for c in ue['profiles'][family] if c['base']==data['path']);tracks={v['bone']:v for v in layer['tracks']};out={}
 for j,n in enumerate(names):
  a=unpack(data['poses'][str(i)][j]);b=unpack(data['poses'][str(min(i+1,data['keys']-1))][j]);p=a[0].lerp(b[0],w);q=a[1].slerp(b[1],w);sc=a[2].lerp(b[2],w)
  if n in tracks:
   dp,dq,ds=sample(tracks[n],t);p+=dp;q=dq@q;sc+=ds
  m=K@Matrix.LocRotScale(p,q,sc)@K;out[n]=m
 return out
def mixed(a,b,w):
 out={}
 for n in names:
  p,q,sc=a[n].decompose();pp,qq,ss=b[n].decompose();out[n]=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
 return out
def component(local):
 out={}
 for n in names:out[n]=out[parents[n]]@local[n] if parents[n] else local[n]
 return out
def smooth(a,b,x):
 w=max(0,min(1,(x-a)/(b-a)));return w*w*(3-2*w)
def runtime(progress,loop_phase=0,family='base'):
 # Same local blend order and weights as M4TacticalSprintComponent/anim proxy.
 a=local_pose('sprint_enter',progress*.5,family);b=local_pose('sprint_loop',loop_phase%1,family)
 pose=mixed(a,b,smooth(.65,1,progress));pose=mixed(local_pose('idle',0,family),pose,smooth(0,.15,progress))
 return component(pose)
def render(row,filename,view='game',extended=False):
 set_pose(row);morphs();r.matrix_world=Matrix.Identity(4)
 ext=bpy.data.objects.get('M24_Magazine10');bpy.data.objects['M24_clip'].hide_render=extended
 if ext:ext.hide_render=not extended;ext.matrix_world=row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
 if view=='game':
  r.matrix_world=cs@C
  if ext:ext.matrix_world=cs@C@row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
 else:
  target=(row['lowerarm_l'].translation+row['hand_l'].translation)*.5
  off=Vector((-.32,-.05,.15)) if view=='left' else Vector((.25,.13,.15))
  cam.location=target+off;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.42
 s.render.filepath=str(filename);bpy.ops.render.render(write_still=True)
setup_render();s.render.resolution_x=960;s.render.resolution_y=540
folder=O/phase;folder.mkdir(exist_ok=True)
for p,ph in ((0,0),(.15,.15),(.3,.3),(.5,.5),(.65,.65),(.8,.8),(1,0),(1,.25),(1,.5),(1,.75)):
 row=runtime(p,ph);render(row,folder/f'game_{p:.2f}_{ph:.2f}.png')
for p in (.3,.65,1):
 for view in ('left','right'):render(runtime(p,.25),folder/f'{view}_{p:.2f}.png',view)
render(runtime(1,.25,'mag10'),folder/'game_mag10.png',extended=True)
idle=component(local_pose('idle',0));report={'origin':ue.get('snapshot_origin'),'max_grip_error_mm':0.,'max_grip_rotation_error_degrees':0.,'max_bone_length_error_mm':0.,'poses':0,'timeline':[],'runtime_game_tested':False}
grips={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('l','r')}
def check(row):
 for side in ('l','r'):
  g=row['WPN_root'].inverted()@row['hand_'+side]
  report['max_grip_error_mm']=max(report['max_grip_error_mm'],(g.translation-grips[side].translation).length*1000)
  q=g.to_quaternion().inverted()@grips[side].to_quaternion();angle=q.angle;angle=min(angle,2*math.pi-angle)
  report['max_grip_rotation_error_degrees']=max(report['max_grip_rotation_error_degrees'],math.degrees(angle))
  for n,parent in (('lowerarm_'+side,'upperarm_'+side),('hand_'+side,'lowerarm_'+side)):
   report['max_bone_length_error_mm']=max(report['max_bone_length_error_mm'],abs((row[n].translation-row[parent].translation).length-(idle[n].translation-idle[parent].translation).length)*1000)
 report['poses']+=1
for p in np.linspace(0,1,121):
 for ph in (0,.25,.5,.75):check(runtime(float(p),ph))
for ph in np.linspace(0,1,121):check(runtime(1,float(ph)))
(O/(phase+'_report.json')).write_text(json.dumps(report,indent=2));print('SPRINT_REVIEW',json.dumps(report),flush=True)
