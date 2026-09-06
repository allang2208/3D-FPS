import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-skin-v05-20260906/foreman-skin-v05.blend'))
s=bpy.context.scene;a=bpy.data.objects['ForemanRig'];body=bpy.data.objects['ForemanBody'];whip=bpy.data.objects['Whip'];FPS=80;s.render.fps=FPS
exec((R/'prepare_grip.py').read_text())
exec((R/'long_whip.py').read_text())
rest={b.name:b.matrix_local.copy() for b in a.data.bones};defs={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in a.data.bones};lengths={n:(t-h).length for n,(h,t) in defs.items()}
def curve(t,keys):
 t=max(keys[0][0],min(keys[-1][0],t))
 def slope(i):
  if i==0 or i==len(keys)-1:return keys[i][1]*0
  h0=keys[i][0]-keys[i-1][0];h1=keys[i+1][0]-keys[i][0];p=(keys[i][1]-keys[i-1][1])/h0;q=(keys[i+1][1]-keys[i][1])/h1
  def mono(x,y):return 0 if x*y<=0 else 3*(h0+h1)/((2*h1+h0)/x+(h1+2*h0)/y)
  return Vector([mono(x,y) for x,y in zip(p,q)]) if isinstance(p,Vector) else mono(p,q)
 for i,((ta,va),(tb,vb)) in enumerate(zip(keys,keys[1:])):
  if t<=tb:
   dt=tb-ta;u=(t-ta)/dt;return (2*u**3-3*u*u+1)*va+(u**3-2*u*u+u)*dt*slope(i)+(-2*u**3+3*u*u)*vb+(u**3-u*u)*dt*slope(i+1)
 return keys[-1][1]
def vk(rows):return [(t,Vector(v)) for t,v in rows]
def rot(pitch=0,twist=0,roll=0):return Matrix.Rotation(twist,3,'Z')@Matrix.Rotation(roll,3,'Y')@Matrix.Rotation(pitch,3,'X')
def matrix(n,h,d,basis=None):
 base=(basis or Matrix.Identity(3))@rest[n].to_3x3();q=(base@Vector((0,1,0))).rotation_difference(d.normalized());m=(q.to_matrix()@base).to_4x4();m.translation=h;a.pose.bones[n].matrix=m;bpy.context.view_layer.update();return m

def limb_matrix(n,h,d,plane,rest_plane):
 y=d.normalized();x=plane.normalized();z=x.cross(y).normalized();x=y.cross(z).normalized()
 ry=(defs[n][1]-defs[n][0]).normalized();rx=rest_plane.normalized();rz=rx.cross(ry).normalized();rx=ry.cross(rz).normalized()
 frame=Matrix((x,y,z)).transposed();rf=Matrix((rx,ry,rz)).transposed()
 m=(frame@rf.transposed()@rest[n].to_3x3()).to_4x4();m.translation=h;a.pose.bones[n].matrix=m;bpy.context.view_layer.update();return m

def two(h,target,l1,l2,pole):
 delta=target-h;dist=max(.001,min(delta.length,(l1+l2)*.985));u=delta.normalized();x=(l1*l1-l2*l2+dist*dist)/(2*dist);v=pole-u*pole.dot(u)
 if v.length<.001:v=Vector((1,0,0))-u*u.x
 v.normalize();return h+u*x+v*math.sqrt(max(0,l1*l1-x*x)),h+u*dist
atk=vk([(0,(.07,0,.02,0)),(.18,(-.04,-.18,.045,0)),(.37,(-.16,-.48,.035,.08)),(.49,(.20,-.08,.095,.25)),(.59625,(.54,.39,.18,.36)),(.72,(.56,.44,.19,.36)),(.91,(.37,.28,.13,.28)),(1.18,(.13,.06,.045,.08)),(1.5,(.07,0,.02,0))])
right=vk([(0,(-.20,-.12,-.65)),(.12,(-.34,.05,-.43)),(.24,(-.27,.22,.12)),(.35,(-.08,.20,.58)),(.42,(-.07,.09,.56)),(.47,(-.30,-.20,.40)),(.52,(-.39,-.28,.05)),(.565,(-.32,-.25,-.38)),(.59625,(-.19,-.20,-.63)),(.68,(-.16,-.15,-.69)),(.84,(-.19,-.10,-.67)),(1.12,(-.23,-.12,-.63)),(1.5,(-.20,-.12,-.65))])
left=vk([(0,(.22,-.12,-.64)),(.20,(.27,-.25,-.43)),(.37,(.30,-.34,-.30)),(.50,(.23,-.18,-.36)),(.64,(.18,.02,-.49)),(.82,(.23,.08,-.57)),(1.13,(.23,-.06,-.60)),(1.5,(.22,-.12,-.64))])

death=vk([(0,(.07,0,1.21,0)),(.16,(.13,.015,1.18,0)),(.34,(.04,.10,.96,0)),(.54,(-.24,.25,.61,.12)),(.73,(-.83,.41,.36,.42)),(.94,(-1.40,.52,.25,.80)),(1.12,(-1.57,.56,.24,1)),(1.4,(-1.57,.56,.24,1))])
report={'clips':{'Idle':1.,'Walk':1.5,'Attack':1.5,'Death':1.4,'Howl':3.},'matching_speed_mps':.40/(1.5*.62),'contact_s':.59625,'ground_corrections':{},'bone_count':len(rest)}
def pose(t,clip):
 for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 phase=t/1.5;lean=.07;twist=0;drop=.02;step=0;sway=0;hip_y=.06
 if clip=='Attack':lean,twist,drop,step=curve(t,atk)
 if clip=='Walk':
  lean+=.018*math.sin(phase*math.tau-.35);twist=.055*math.sin(phase*math.tau);drop=.047+.018*math.cos(phase*math.tau*2);sway=.052*math.sin(phase*math.tau-.25)
 if clip=='Idle':lean+=.010*math.sin(t*math.tau);drop+=.004*(1-math.cos(t*math.tau));twist=.006*math.sin(t*math.tau-.35)
 base=Vector((sway,hip_y,1.23-drop));d=None
 if clip=='Death':d=curve(t,death);lean=d.x;base=Vector((.022*math.sin(math.pi*t/1.4)**2,d.y+.06,d.z))
 mats={};head=base
 for i,n in enumerate(['pelvis','spine','chest','neck','head']):
  pitch=lean*[.35,.72,1,.76,.68][i];yaw=twist*[.5,.77,1,.80,.74][i];roll=-sway*[.15,.4,.6,.32,.20][i]
  if clip=='Attack':
   delayed=curve(t-([-.025,0,0,.022,.04][i]),atk);pitch=delayed.x*[.35,.72,1,.76,.68][i];yaw=delayed.y*[.5,.77,1,.80,.74][i]
  if clip=='Death':
   p=curve(t-[0,.018,.035,.055,.07][i],death);pitch=p.x+math.sin(math.pi*min(1,t/1.12))**2*[0,.10,.19,.22,.12][i];yaw=0
  basis=rot(pitch,yaw,roll);m=mats[n]=matrix(n,head,basis@Vector((0,0,lengths[n])),basis);head=m.translation+(m.to_3x3()@Vector((0,lengths[n],0)))
 cd=mats['chest']@rest['chest'].inverted();pd=mats['pelvis']@rest['pelvis'].inverted();cb=cd.to_3x3().normalized();grip=None
 for side,sign in [('L',1),('R',-1)]:
  cl='clavicle.'+side;ua='upper_arm.'+side;fa='forearm.'+side;ha='hand.'+side
  sh=cd@defs[cl][1];ch=cd@defs[cl][0]
  if clip=='Attack':
   lift=curve(t,[(0,0),(.35,.045 if side=='R' else .015),(.6,.015),(1.5,0)]);sh.z+=lift
  matrix(cl,ch,sh-ch,cb)
  offset=Vector((sign*(.22 if side=='L' else .20),-.12,-(.64 if side=='L' else .65)))
  if clip=='Attack':offset=curve(t,left if side=='L' else right)
  if clip=='Walk':
   phase_arm=phase*math.tau+(0 if side=='L' else math.pi)-.35;offset.y+=.11*math.sin(phase_arm);offset.z+=.012*math.cos(phase_arm)
  if clip=='Idle':offset.y+=.006*math.sin(t*math.tau-.50);offset.z+=.004*math.sin(t*math.tau-.25)
  target=sh+cb@offset;pole=cb@Vector((sign*.35,.90,.05))
  if clip=='Death':
   fall=curve(t,[(0,0),(.46,.12),(.74,.47),(1.09,1),(1.4,1)]);lag=curve(t-(.05 if side=='R' else 0),[(0,0),(.55,.12),(.84,.62),(1.15,1),(1.4,1)])
   offset=Vector((sign*.22,-.12-.16*math.sin(math.pi*min(1,t/1.1)),-.65)).lerp(Vector((sign*.20,-.59,-.035)),lag)
   target=sh+offset;target.z=max(.13,target.z);pole=Vector((sign*.7,.18,.22))
  elbow,wrist=two(sh,target,lengths[ua],lengths[fa],pole)
  plane=(elbow-sh).cross(wrist-elbow).normalized();rest_plane=(defs[ua][1]-defs[ua][0]).cross(defs[fa][1]-defs[fa][0]).normalized()
  um=limb_matrix(ua,sh,elbow-sh,plane,rest_plane)
  fm=limb_matrix(fa,elbow,wrist-elbow,plane,rest_plane);fb=(fm@rest[fa].inverted()).to_3x3().normalized()
  hdir=(wrist-elbow).normalized()
  if clip=='Attack':
   # Small delayed wrist flexion, always relative to the forearm frame.
   flex=curve(t-.015 if side=='R' else t-.04,[(0,.10),(.36,-.18),(.48,-.24),(.59625,.40),(.72,.25),(.96,.13),(1.5,.10)])
   hdir=(fb@Matrix.Rotation(flex,3,'X')@rest[fa].to_3x3()@Vector((0,1,0))).normalized()
  elif clip=='Walk':hdir=(hdir+cb@Vector((0,.04*math.sin(phase*math.tau-.7),-.10))).normalized()
  hm=matrix(ha,wrist,hdir,fb)
  # Anchor in the actual mesh palm, transformed from bind coordinates.
  hand_delta=hm@rest[ha].inverted()
  fingers=a.pose.bones['fingers_cup.'+side]
  axis=rest[fingers.name].to_3x3().inverted()@Vector((0,sign,0))
  curl=.88 if side=='R' else .19
  if clip=='Attack':curl+=(.10 if side=='R' else -.16)*math.sin(math.pi*t/1.5)**2
  if clip=='Death':curl*=1-.6*min(1,max(0,(t-.65)/.65))
  fingers.rotation_mode='QUATERNION';fingers.rotation_quaternion=Quaternion(axis,curl)
  fingertip=a.pose.bones['fingers_tip.'+side];fingertip.rotation_mode='QUATERNION'
  fingertip.rotation_quaternion=Quaternion(rest[fingertip.name].to_3x3().inverted()@Vector((0,sign,0)),curl*.60)
  thumb=a.pose.bones['thumb.'+side];thumb.rotation_mode='QUATERNION'
  thumb_axis=rest[thumb.name].to_3x3().inverted()@Vector((.8,-sign*.5,0)).normalized()
  thumb.rotation_quaternion=Quaternion(thumb_axis,.85 if side=='R' else .15)
  if side=='R':
   grip=hand_delta@Vector((-.805,-.235,1.18))
   grip_dir=(hand_delta.to_3x3()@Vector((0,-1,0))).normalized()
  th='thigh.'+side;sn='shin.'+side;fo='foot.'+side;hip=pd@defs[th][0];ankle=defs[sn][1].copy()
  if clip=='Walk':
   ph=(phase+(0 if side=='L' else .5))%1;stance=.62;travel=.40
   if ph<stance:ankle.y+=-travel/2+travel*ph/stance
   else:
    q=(ph-stance)/(1-stance);ankle.y+=travel/2-travel*q*q*(3-2*q)+travel*(1-stance)/stance*q*(1-q)*(1-2*q);ankle.z+=.075*math.sin(math.pi*q)**2
  if clip=='Attack' and side=='L':
   ankle.y-=step
   if .27<t<.57:ankle.z+=.055*math.sin(math.pi*(t-.27)/.30)**2
   if .87<t<1.40:ankle.z+=.035*math.sin(math.pi*(t-.87)/.53)**2
  if clip=='Death':
   extend=curve(t-(.04 if side=='R' else 0),death).w;ankle.y-=.70*extend;ankle.z+=.13*math.sin(math.pi*extend);ankle.x+=sign*.06*extend
  knee,ankle=two(hip,ankle,lengths[th],lengths[sn],Vector((sign*.08,-1,.05)))
  matrix(th,hip,knee-hip);matrix(sn,knee,ankle-knee)
  fd=defs[fo][1]-defs[fo][0]
  if clip=='Death':fd=rot(-.45*d.w)@fd
  matrix(fo,ankle,fd)
 bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();pre_low=min((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear()
 animate_long_whip(a,grip,grip_dir,t,clip,curve,ground_z=.02+pre_low)
 bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();low=min((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear()
 # Root local Z is NOT world vertical. Set root matrix translation in arm space.
 root=a.pose.bones['root'];m=root.matrix.copy();m.translation.z+=.005-low;root.matrix=m;bpy.context.view_layer.update()
 return .005-low
for name,duration in [('Idle',1.),('Walk',1.5),('Attack',1.5),('Death',1.4)]:
 a.animation_data.action=None
 old=bpy.data.actions.get(name)
 if old:bpy.data.actions.remove(old)
 act=bpy.data.actions.new(name);act.use_fake_user=True;a.animation_data.action=act;previous={};corrections=[]
 for t in sorted(set([i/FPS for i in range(round(duration*FPS)+1)]+([.59625] if name=='Attack' else []))):
  corrections.append(pose(t,name))
  for pb in a.pose.bones:
   pb.rotation_mode='QUATERNION'
   if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
   previous[pb.name]=pb.rotation_quaternion.copy()
   for c in ['location','rotation_quaternion','scale']:pb.keyframe_insert(c,frame=t*FPS,group=pb.name)
 for slot in act.slots:
  for layer in act.layers:
   for strip in layer.strips:
    bag=strip.channelbag(slot)
    if bag:
     for fc in bag.fcurves:
      for k in fc.keyframe_points:k.interpolation='LINEAR'
 report['ground_corrections'][name]=[min(corrections),max(corrections)]
exec((R/'finish_howl.py').read_text())
a.animation_data.action=bpy.data.actions['Idle'];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-downstroke-v07.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [a,body,whip,bpy.data.objects['WhipHandle']]:o.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'foreman-downstroke-v07.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
(R/'build-report.json').write_text(json.dumps(report,indent=2));print('FOREMAN_V07_BUILD',json.dumps(report))
