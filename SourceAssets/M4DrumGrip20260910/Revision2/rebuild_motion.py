import bpy,math,json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT.parent))
from preview_setup import setup
r,s,drum=setup();rest=r.data.bones
grip=json.loads((OUT/'anatomical_grip.json').read_text());grip_wrist=Matrix(grip['wrist_in_drum']);finger_names=list(grip['fingers']);closed={n:Matrix(m) for n,m in grip['fingers'].items()}
data=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(data['source_to_component']);center=Vector(data['center']);bind=rest['WPN_SOCKET_Magazine'].matrix_local.copy();component=bind.inverted()@G@Matrix.Translation(center)
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def blend(a,b,t):
 p,q,z=a.decompose();P,Q,Z=b.decompose();return Matrix.LocRotScale(p.lerp(P,t),q.slerp(Q,t),z.lerp(Z,t))
def track(keys,t):
 if t<=keys[0][0]:return keys[0][1].copy()
 if t>=keys[-1][0]:return keys[-1][1].copy()
 for i in range(len(keys)-1):
  t0,m0=keys[i];t1,m1=keys[i+1]
  if t<=t1:
   u=(t-t0)/(t1-t0);p,q,z=m0.decompose();P,Q,Z=m1.decompose()
   if i==0:v0=Vector()
   else:v0=(P-keys[i-1][1].translation)/(t1-keys[i-1][0])
   if i+2>=len(keys):v1=Vector()
   else:v1=(keys[i+2][1].translation-p)/(keys[i+2][0]-t0)
   if (P-p).length<1e-6:v0=Vector();v1=Vector()
   loc=(2*u**3-3*u*u+1)*p+(u**3-2*u*u+u)*(t1-t0)*v0+(-2*u**3+3*u*u)*P+(u**3-u*u)*(t1-t0)*v1
   return Matrix.LocRotScale(loc,q.slerp(Q,smooth(u)),z.lerp(Z,u))
shoulders={};source_globals={}
def make_press_pose():
 f=(rest['middle_01_l'].head_local-rest['hand_l'].head_local).normalized();across=(rest['pinky_01_l'].head_local-rest['index_01_l'].head_local).normalized();n=f.cross(across).normalized()
 if n.dot(rest['middle_01_l'].matrix_local.to_3x3().col[1])<0:n.negate()
 src=Matrix((f,n.cross(f),n)).transposed();F=Vector((-1,0,0));N=Vector((0,-1,0));dst=Matrix((F,N.cross(F),N)).transposed()
 mats={'hand_l':(dst@src.transposed()@rest['hand_l'].matrix_local.to_3x3()).to_4x4()};basis={}
 for name in finger_names:
  q=Quaternion()
  if 'metacarpal' not in name:
   digit,j,_=name.split('_');j=int(j);angles=[-32,-5,-5] if digit=='index' else ([5,15,15] if digit=='thumb' else [18,55,32]);q=Quaternion((0,0,1),math.radians(angles[j-1]))
   if digit=='thumb' and j==1:q=Quaternion((0,1,0),math.radians(20))@q
  basis[name]=q.to_matrix().to_4x4();parent=rest[name].parent.name;mats[name]=mats[parent]@rest[parent].matrix_local.inverted()@rest[name].matrix_local@basis[name]
 hm=bpy.data.objects['SK_Manny_Arms_Export'];gi=hm.vertex_groups['index_03_l'].index;transform=mats['index_03_l']@rest['index_03_l'].matrix_local.inverted()@hm.matrix_world
 points=[transform@v.co for v in hm.data.vertices if any(g.group==gi and g.weight>.8 for g in v.groups)];points.sort(key=lambda v:v.x);pad=sum(points[:10],Vector())/10
 mats['hand_l'].translation=Vector((.0195,-.0934,.055))-pad
 return mats['hand_l'],basis
press_hand,press_fingers=make_press_pose()
def arm_to(goal,pole_hint,side='l'):
 un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
 a=shoulders[side].copy();target=goal.translation
 rest_u=rest[fn].head_local-rest[un].head_local;rest_v=rest[hn].head_local-rest[fn].head_local
 l1=rest_u.length;l2=rest_v.length;rest_u.normalize();rest_v.normalize();rest_hinge=rest_v.cross(rest_u).normalized()
 src_upper=Matrix((rest_u,rest_hinge.cross(rest_u),rest_hinge)).transposed();src_lower=Matrix((rest_v,rest_hinge.cross(rest_v),rest_hinge)).transposed()
 delta=target-a;dist=delta.length;axis=delta.normalized()
 if dist>=l1+l2-.001:raise RuntimeError('Unreachable left hand '+str((s.frame_current,dist,l1+l2)))
 desired_forearm=goal.to_3x3()@rest[hn].matrix_local.to_3x3().inverted()
 ideal_elbow=target-(desired_forearm@rest_v)*l2
 ideal_pole=ideal_elbow-a-axis*(ideal_elbow-a).dot(axis)
 pole=pole_hint-axis*pole_hint.dot(axis);pole.normalize()
 pole=ideal_pole.normalized().lerp(pole,.20).normalized();along=(l1*l1-l2*l2+dist*dist)/(2*dist)
 if side=='r':
  pole=source_globals[fn].translation-a;pole-=axis*pole.dot(axis);pole.normalize()
 elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along));u=(elbow-a).normalized();v=(target-elbow).normalized();hinge=v.cross(u).normalized()
 if side=='r':
  old_u=(source_globals[fn].translation-source_globals[un].translation).normalized();old_v=(source_globals[hn].translation-source_globals[fn].translation).normalized()
  upper=Matrix.LocRotScale(a,old_u.rotation_difference(u)@source_globals[un].to_quaternion(),Vector((1,1,1)));lower=Matrix.LocRotScale(elbow,old_v.rotation_difference(v)@source_globals[fn].to_quaternion(),Vector((1,1,1)))
  for name,m in [(un,upper),(fn,lower)]:r.pose.bones[name].matrix=m;bpy.context.view_layer.update()
  expected=lower.to_quaternion()@source_globals[fn].to_quaternion().inverted()@source_globals[hn].to_quaternion();delta=goal.to_quaternion()@expected.inverted();projection=Vector((delta.x,delta.y,delta.z)).dot(v)
  extra=2*math.atan2(projection,delta.w)
  for name,fraction in [('lowerarm_twist_02_r',1/3),('lowerarm_twist_01_r',2/3)]:
   base=lower@source_globals[fn].inverted()@source_globals[name];r.pose.bones[name].matrix=Matrix.LocRotScale(base.translation,Quaternion(v,extra*fraction)@base.to_quaternion(),Vector((1,1,1)));bpy.context.view_layer.update()
  r.pose.bones[hn].matrix=goal;bpy.context.view_layer.update();return 0,0
 lower_rot=Matrix((v,hinge.cross(v).normalized(),hinge)).transposed()@src_lower.transposed()@rest[fn].matrix_local.to_3x3()
 lower=Matrix.LocRotScale(elbow,lower_rot.to_quaternion(),Vector((1,1,1)))
 old_u=(source_globals[fn].translation-source_globals[un].translation).normalized();swing=old_u.rotation_difference(u)
 upper_base=Matrix.LocRotScale(a,swing@source_globals[un].to_quaternion(),Vector((1,1,1)))
 base_z=upper_base.to_3x3()@rest[un].matrix_local.to_3x3().inverted()@rest_hinge;upper_twist=math.atan2(u.dot(base_z.cross(hinge)),base_z.dot(hinge))
 upper=upper_base
 # Match the true rest longitudinal axis (Manny export uses local X along limbs).
 for n,m in [(un,upper),(fn,lower)]:r.pose.bones[n].matrix=m;bpy.context.view_layer.update()
 for name,fraction in [('upperarm_twist_01_'+side,1/3),('upperarm_twist_02_'+side,2/3)]:
  base=upper@rest[un].matrix_local.inverted()@rest[name].matrix_local
  r.pose.bones[name].matrix=Matrix.LocRotScale(base.translation,Quaternion(u,upper_twist*fraction)@base.to_quaternion(),Vector((1,1,1)));bpy.context.view_layer.update()
 # Spread wrist pronation over the two forearm twist bones, avoiding a single cuff twist.
 desired_z=desired_forearm@rest_hinge;desired_z-=v*desired_z.dot(v);desired_z.normalize()
 twist=math.atan2(v.dot(hinge.cross(desired_z)),hinge.dot(desired_z))
 for name,fraction in [('lowerarm_twist_02_'+side,1/3),('lowerarm_twist_01_'+side,2/3)]:
  base=lower@rest[fn].matrix_local.inverted()@rest[name].matrix_local
  q=Quaternion(v,twist*fraction)@base.to_quaternion();r.pose.bones[name].matrix=Matrix.LocRotScale(base.translation,q,Vector((1,1,1)))
  bpy.context.view_layer.update()
 r.pose.bones[hn].matrix=goal;bpy.context.view_layer.update()
 neutral=Quaternion(v,twist)@lower.to_quaternion()@rest[fn].matrix_local.to_quaternion().inverted()@rest[hn].matrix_local.to_quaternion()
 angle=math.degrees(neutral.rotation_difference(goal.to_quaternion()).angle);angle=min(angle,360-angle)
 return math.degrees(twist),angle
def offset(x,y,z,tilt=0,roll=0):return Matrix.LocRotScale(Vector((x,y,z)),Quaternion((1,0,0),math.radians(roll))@Quaternion((0,1,0),math.radians(tilt)),Vector((1,1,1)))
specs={
 'reload':{'end':126,'approach':4,'lock':23,'seat':95,'release':116,'keys':[(0,0,0,0,0),(25,0,0,0,0),(29,0,0,-.025,0),(39,.055,.02,-.18,-12),(50,.095,.10,-.30,-20),(56,.085,.11,-.29,-12),(67,.05,.03,-.16,10),(76,.008,0,-.065,3),(88,0,0,-.018,0),(95,0,0,0,0),(126,0,0,0,0)]},
 'reload_empty':{'end':162,'approach':1,'lock':15,'seat':80,'release':99,'keys':[(0,0,0,0,0),(18,0,0,0,0),(21,0,0,-.025,0),(29,.07,.06,-.25,-15),(35,.09,.10,-.30,-18),(43,.06,.055,-.22,6),(54,.009,0,-.07,3),(70,0,0,-.022,0),(80,0,0,0,0),(162,0,0,0,0)]}}
report={}
for clip,cfg in specs.items():
 end=cfg['end'];a=bpy.data.actions['M4_HK416_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];sources=[]
 for t in range(end+1):
  s.frame_set(t);bpy.context.view_layer.update();sources.append({'basis':{b.name:b.matrix_basis.copy() for b in r.pose.bones},'global':{b.name:b.matrix.copy() for b in r.pose.bones}})
 r.animation_data.action=None
 # Match the drum support pose: 32 mm forward from the original reference
 # (20 mm beyond M4ContactImpactFinal), inherited through the left clavicle.
 for n,m in sources[0]['basis'].items():r.pose.bones[n].matrix_basis=m
 bpy.context.view_layer.update()
 clav=r.pose.bones['clavicle_l'];m=clav.matrix.copy();m.translation+=sources[0]['global']['WPN_root'].to_3x3()@Vector((0,-.032,0));clav.matrix=m;bpy.context.view_layer.update()
 sources[0]={'basis':{b.name:b.matrix_basis.copy() for b in r.pose.bones},'global':{b.name:b.matrix.copy() for b in r.pose.bones}}
 shoulders={side:sources[0]['global']['upperarm_'+side].translation.copy() for side in ['l','r']}
 source_globals=sources[0]['global']
 gun0=sources[0]['global']['WPN_root'];pivot=sources[0]['global']['hand_r'].translation
 turn=Quaternion((1,0,0),math.radians(30))@Quaternion((0,1,0),math.radians(20))
 braced=Matrix.Translation(pivot)@turn.to_matrix().to_4x4()@Matrix.Translation(-pivot)@gun0;braced.translation+=Vector((0,-.015,-.005))
 brace_end=98 if clip=='reload' else 139
 gun_keys=[(0,gun0),(16,braced),(brace_end,braced),(end,gun0)]
 installed=sources[0]['global']['WPN_root'].inverted()@sources[0]['global']['WPN_SOCKET_Magazine']@component
 # Deliberate path, independent of the standard magazine's offscreen discontinuity.
 path=[(k[0],offset(*k[1:],roll=max(0,(-k[3]-.065)/.235)*68)) for k in cfg['keys']]
 key_times=sorted(set([0,4,8,12,cfg['seat'],cfg['release']]+list(range(cfg['release'],end+1,5))+[end]+([130] if clip=='reload_empty' else [])))
 smooth_hand_keys=[(t,sources[t]['global']['WPN_root'].inverted()@sources[t]['global']['hand_l']) for t in key_times]
 finger_keys={n:[(t,sources[t]['basis'][n]) for t in key_times] for n in finger_names}
 if clip=='reload_empty':
  seated=installed@grip_wrist;clear=seated.copy();clear.translation+=installed.to_3x3()@Vector((.045,0,-.025))
  press=press_hand.copy();ready=press.copy();ready.translation+=Vector((.025,0,0))
  home=gun0.inverted()@sources[0]['global']['hand_l']
  smooth_hand_keys=[(80,seated),(98,clear),(116,ready),(126,press),(130,press),(137,ready),(154,home),(162,home)]
  for n in finger_names:
   p,q,z=closed[n].decompose()
   if 'metacarpal' not in n and not n.startswith('thumb'):q=Quaternion((0,0,1),math.radians(-25 if '_01_' in n else 0))
   relaxed=Matrix.LocRotScale(p,q,z);press_finger=press_fingers[n]
   finger_keys[n]=[(0,sources[0]['basis'][n]),(80,closed[n]),(96,relaxed),(116,press_finger),(133,press_finger),(141,relaxed),(154,sources[0]['basis'][n]),(162,sources[0]['basis'][n])]
 samples=[];stats=[]
 for t in range(end+1):
  s.frame_set(t)
  for n,m in sources[0]['basis'].items():r.pose.bones[n].matrix_basis=m
  bpy.context.view_layer.update()
  gun=track(gun_keys,t)
  for n in r.pose.bones.keys():
   if n.startswith('WPN'):
    r.pose.bones[n].matrix=gun@sources[t]['global']['WPN_root'].inverted()@sources[t]['global'][n];bpy.context.view_layer.update()
  # The viewmodel moves forward during reload. Lower the open upper-arm end
  # before it reaches the camera plane; retain arm lengths and weapon contact.
  drop=Vector((0,0,-.18))*smooth(t/6)*smooth((end-t)/10)
  clav=r.pose.bones['clavicle_r'];m=clav.matrix.copy();m.translation+=drop;clav.matrix=m;bpy.context.view_layer.update()
  shoulders['r']=sources[0]['global']['upperarm_r'].translation+drop
  right_goal=gun@gun0.inverted()@sources[0]['global']['hand_r'];arm_to(right_goal,Vector((.75,-.15,-.65)),'r')
  D=gun@installed@track(path,t)
  r.pose.bones['WPN_SOCKET_Magazine'].matrix=D@component.inverted();bpy.context.view_layer.update()
  entry=smooth((t-cfg['approach'])/(cfg['lock']-cfg['approach']));leave=smooth((t-(cfg['seat']+3))/(cfg['release']-cfg['seat']-3));weight=entry*(1-leave)
  source_hand=gun@track(smooth_hand_keys,t) if clip=='reload_empty' and t>cfg['seat'] else gun@gun0.inverted()@sources[0]['global']['hand_l']
  if clip=='reload_empty' and t>132:
   reach=source_hand.translation-shoulders['l']
   if reach.length>.535:source_hand.translation=shoulders['l']+reach.normalized()*.535
  target=D@grip_wrist
  if cfg['lock']<=t<=cfg['seat'] and (target.translation-shoulders['l']).length>.533:
   shoulder=shoulders['l'];delta=shoulder+(target.translation-shoulder).normalized()*.533-target.translation
   # Loose-magazine path remains within arm reach; seated pose is never moved.
   if t<cfg['seat']-5:
    D.translation+=delta;target=D@grip_wrist;r.pose.bones['WPN_SOCKET_Magazine'].matrix=D@component.inverted();bpy.context.view_layer.update()
  # Approach around the outside, then close in; release clears the drum before returning.
  arc=math.sin(math.pi*entry)*.055 if t<cfg['lock'] else math.sin(math.pi*leave)*.065
  target.translation+=D.to_3x3()@Vector((arc,0,-arc*.3))
  goal=blend(source_hand,target,weight)
  clearance=math.sin(math.pi*entry) if t<cfg['lock'] else math.sin(math.pi*leave)
  goal.translation+=D.to_3x3()@Vector((clearance*.105,0,0))
  if clip=='reload_empty' and t>cfg['seat']:
   goal=source_hand.copy();weight=0;opening=0
  # Continuous left/down elbow pole, blended to source near entry/exit.
  sg=sources[0]['global'];src_pole=sg['lowerarm_l'].translation-sg['upperarm_l'].translation
  pole=src_pole.normalized().lerp(Vector((-.75,-.10,-.65)).normalized(),weight*.85).normalized()
  twist,wrist=arm_to(goal,pole)
  opening=math.sin(math.pi*entry)*.90 if t<cfg['lock'] else math.sin(math.pi*leave)*.90
  for n in finger_names:
   b=r.pose.bones[n];closed_pose=closed[n];p,q,z=closed_pose.decompose()
   if 'metacarpal' not in n:
    digit,j,_=n.split('_');j=int(j)
    # Open by reducing flexion, never by arbitrarily rotating finger joints in 3D.
    if digit!='thumb':q=q.slerp(Quaternion((0,0,1),math.radians(-32 if j==1 else -5)),opening)
    else:q=q.slerp(Quaternion((0,1,0),math.radians(25)),opening*.45)
   b.matrix_basis=blend(track(finger_keys[n],t),Matrix.LocRotScale(p,q,z),weight)
  bpy.context.view_layer.update();samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
  stats.append({'frame':t,'twist_deg':twist,'wrist_residual_deg':wrist,'hand':list(r.pose.bones['hand_l'].head),'magazine':list(r.pose.bones['WPN_SOCKET_Magazine'].head),'pole':list(pole)})
 # Evaluate actual glove volume over the entire transition, then apply a smooth
 # outside clearance only while the hand is free. Locked grip geometry is unchanged.
 hm=bpy.data.objects['SK_Manny_Arms_Export'];groupids={g.index for g in hm.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))}
 ids=np.array([v.index for v in hm.data.vertices if sum(g.weight for g in v.groups if g.group in groupids)>.7]);raw=[]
 for t in range(end+1):
  s.frame_set(t)
  for n,m in samples[t].items():r.pose.bones[n].matrix_basis=m
  bpy.context.view_layer.update();D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@component
  ev=hm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();coords=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coords)
  points=coords.reshape(-1,3)[ids];points=(np.array(D.inverted()@ev.matrix_world)@np.column_stack((points,np.ones(len(points)))).T).T[:,:3];ev.to_mesh_clear()
  mask=(np.abs(points[:,1])<.038)&(np.abs(points[:,2]+.085)<.073)
  inside=points[mask];needed=np.sqrt(np.maximum(0,.073**2-(inside[:,2]+.085)**2))+.002-inside[:,0]
  amount=max(0,float(needed.max())) if len(needed) else 0
  if cfg['lock']<=t<=cfg['seat']:amount=0
  raw.append(amount)
 for t in range(end+1):
  push=max(raw[j]*math.exp(-.5*((j-t)/2.5)**2) for j in range(max(0,t-10),min(end,t+10)+1))
  if cfg['lock']<=t<=cfg['seat']:push=0
  elif t<cfg['lock']:push*=smooth((cfg['lock']-t)/4)
  elif t>cfg['seat']:push*=smooth((t-cfg['seat'])/4)
  if push<=.00001:continue
  s.frame_set(t)
  for n,m in samples[t].items():r.pose.bones[n].matrix_basis=m
  bpy.context.view_layer.update();D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@component;goal=r.pose.bones['hand_l'].matrix.copy();goal.translation+=D.to_3x3()@Vector((push,0,0))
  twist,wrist=arm_to(goal,Vector(stats[t]['pole']));stats[t]['clearance_cm']=push*100;stats[t]['twist_deg']=twist;stats[t]['wrist_residual_deg']=wrist
  samples[t]={b.name:b.matrix_basis.copy() for b in r.pose.bones}
 # The runtime blends local poses. Start/end at the exact authored idle limb
 # relationship instead of entering a different IK elbow plane in one frame.
 for t,poses in enumerate(samples):
  w=smooth(t/(8 if clip=='reload' else 6))*smooth((end-t)/12)
  for n in poses:
   if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand')):poses[n]=blend(sources[0]['basis'][n],poses[n],w)
 action=bpy.data.actions.new('A_M4_DrumGrip_'+clip);action.use_fake_user=True;r.animation_data.action=action;previous={}
 for t,poses in enumerate(samples):
  for n,m in poses.items():
   b=r.pose.bones[n];p,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b.rotation_mode='QUATERNION';b.location=p;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=t)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(OUT/(action.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[clip]={'config':cfg,'frames':stats}
 folder=OUT/'Frames'/clip;folder.mkdir(parents=True,exist_ok=True)
 # Stable character-left view includes shoulder, elbow, wrist, and both magazine caps.
 for t in ([] if '--no-render' in sys.argv else range(0,end+1,3)):
  s.frame_set(t);bpy.context.view_layer.update();focus=Vector((-.04,.17,-.24));s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.9
  s.camera.location=focus+Vector((-.65,-.45,.1));s.camera.rotation_euler=(focus-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.resolution_x=900;s.render.resolution_y=720;s.render.filepath=str(folder/f'{t:03}.png');bpy.ops.render.render(write_still=True)
 print('REBUILT',clip,'max wrist',max((x['wrist_residual_deg'],x['frame']) for x in stats),'max twist',max(abs(x['twist_deg']) for x in stats),flush=True)
 r.animation_data.action=None
(OUT/'motion_report.json').write_text(json.dumps(report,indent=2))
r.animation_data.action=bpy.data.actions['A_M4_DrumGrip_reload'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=126;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_DrumGrip_Rebuilt.blend'))
