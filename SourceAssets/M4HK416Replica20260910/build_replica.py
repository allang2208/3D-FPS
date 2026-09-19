"""Retarget captured Godot runtime motion onto the existing M4/Manny rig.
All transforms come from Reference/runtime_poses.json; fit corrections are explicit.
Run with Blender 5.1. Source projects and original animation assets are read-only.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'Reference/runtime_poses.json').read_text())
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
# The existing T handle and its two latch pieces are disconnected geometry.
# Give them an independent child bone; preserve every existing rest bone/weight.
r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
rootbind=r.data.bones['WPN_root'].matrix_local.copy()
body=bpy.data.objects['M4_M4 Body_Export'];adj=[[] for v in body.data.vertices]
for e in body.data.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();handleids=[];catchids=[]
for v in body.data.vertices:
 if v.index in seen:continue
 stack=[v.index];seen.add(v.index);ids=[]
 while stack:
  i=stack.pop();ids.append(i)
  for j in adj[i]:
   if j not in seen:seen.add(j);stack.append(j)
 points=[rootbind.inverted()@body.matrix_world@body.data.vertices[i].co for i in ids]
 if len(ids) in [232,50] and min(p.z for p in points)>.087 and min(p.y for p in points)>-.03:handleids+=ids
 if len(ids)==162 and min(p.x for p in points)>.012 and -.098<min(p.y for p in points)<-.096:catchids+=ids
assert len(handleids)==332,len(handleids)
assert len(catchids)==162,len(catchids)
bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.object.mode_set(mode='EDIT')
for name,pivot in [('WPN_ChargingHandle',(0,.01,.095)),('WPN_BoltCatch',(.0152,-.0934,.0418))]:
 b=r.data.edit_bones.new(name);b.length=.025;b.matrix=rootbind@Matrix.Translation(pivot);b.parent=r.data.edit_bones['WPN_root']
bpy.ops.object.mode_set(mode='OBJECT')
body.vertex_groups['WPN_root'].remove(handleids);body.vertex_groups.new(name='WPN_ChargingHandle').add(handleids,1,'REPLACE')
body.vertex_groups['WPN_root'].remove(catchids);body.vertex_groups.new(name='WPN_BoltCatch').add(catchids,1,'REPLACE')
def set_action(a):
 r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(t):
 s.frame_set(int(t),subframe=t-int(t));bpy.context.view_layer.update()
set_action(bpy.data.actions['M4_idle']);frame(0)
base={b.name:b.matrix.copy() for b in r.pose.bones}
rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
names=list(base)
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
def source(f):
 return {b['name']:C@Matrix([m[j:j+4] for j in range(0,16,4)])@C.inverted() for key,rig in data['rigs'].items() for b,m in zip(rig['bones'],f['rigs'][key])}
srcidle=source(data['clips']['idle']['frames'][0])
def gunframe(rear,front,wrist):
 y=(front-rear).normalized();z=rear-wrist;z=(z-y*y.dot(z)).normalized();x=y.cross(z).normalized();z=x.cross(y).normalized()
 result=Matrix((x,y,z)).transposed().to_4x4();result.translation=wrist;return result
S=gunframe(srcidle['RearSight'].translation,srcidle['FrontSight'].translation,srcidle['mixamorig2_RightHand'].translation)
T=gunframe(base['WPN_RearSight'].translation,base['WPN_FrontSight'].translation,base['hand_r'].translation)
D=T@S.inverted();dq=D.to_quaternion();iq=dq.inverted()
R=base['WPN_root'].inverted()@D@srcidle['ARMA']
rootrel={n:base['WPN_root'].inverted()@base[n] for n in names if n.startswith('WPN_')}
local={n:base[parents[n]].inverted()@base[n] if parents[n] else base[n] for n in names}
def palmframe(wrist,index,middle,pinky):
 y=(middle-wrist).normalized();x=(index-pinky).normalized();z=x.cross(y).normalized();x=y.cross(z).normalized();return Matrix((x,y,z)).transposed().to_quaternion()
handmap={}
for side,longside in [('l','Left'),('r','Right')]:
 pre='mixamorig2_'+longside+'Hand'
 hs=palmframe(*[srcidle[n].translation for n in [pre,pre+'Index1',pre+'Middle1',pre+'Pinky1']])
 ht=palmframe(*[base[n+'_'+side].translation for n in ['hand','index_01','middle_01','pinky_01']])
 handmap[side]=ht@hs.inverted()
def smooth(v):
 v=max(0,min(1,v));return v*v*(3-2*v)
def window(t,a,b,c,d):return smooth((t-a)/(b-a))*(1-smooth((t-c)/(d-c)))
def rotation(src,name,target):return dq@src[name].to_quaternion()@srcidle[name].to_quaternion().inverted()@iq@base[target].to_quaternion()
def mapped_point(src,name,target,gunq):return D@src[name].translation+gunq@(base[target].translation-D@srcidle[name].translation)
def adjust_hand(p,side,shift,turn):
 un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
 a=p[un].translation.copy();b=p[fn].translation.copy();c=p[hn].translation.copy()
 l1=(b-a).length;l2=(c-b).length
 for n in names:
  if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
   p[n]=Matrix.LocRotScale(c+turn@(p[n].translation-c)+shift,turn@p[n].to_quaternion(),p[n].to_scale())
 goal=p[hn].translation;axis=(goal-a).normalized();distance=(goal-a).length
 if distance>=l1+l2:a+=axis*(distance-l1-l2+.00001);distance=(goal-a).length
 pole=b-a;pole-=axis*pole.dot(axis);pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
 elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 p[un]=Matrix.LocRotScale(a,(b-p[un].translation).rotation_difference(elbow-a)@p[un].to_quaternion(),p[un].to_scale())
 p[fn]=Matrix.LocRotScale(elbow,(c-b).rotation_difference(goal-elbow)@p[fn].to_quaternion(),p[fn].to_scale())
 for n in names:
  if (n.startswith('upperarm_twist') or n.startswith('lowerarm_twist')) and n.endswith('_'+side):p[n]=p[parents[n]]@local[n]
cache={};report={'source':'Actual Godot HK416 runtime 60 Hz, including AnimationTree and fitted hand pose','clips':{},'bone_count':len(names),'fit_matrix':[list(v) for v in D]}
for clip in ['reload','reload_empty','equip_charge']:
 frames=data['clips'][clip]['frames'];samples=[];maxerr=0;maxreach=0
 for f in frames:
  t=f['time'];src=source(f);delta=D@src['ARMA']@srcidle['ARMA'].inverted()@D.inverted();gq=delta.to_quaternion()
  p={n:m.copy() for n,m in base.items()};root=delta@base['WPN_root']
  # Follow the complete original gun motion; fixed receiver components stay rigid.
  for n in rootrel:p[n]=root@rootrel[n]
  rel=src['ARMA'].inverted()@src['CARGADOR'];oldrel=srcidle['ARMA'].inverted()@srcidle['CARGADOR']
  p['WPN_SOCKET_Magazine']=root@R@rel@oldrel.inverted()@R.inverted()@rootrel['WPN_SOCKET_Magazine']
  # Actual M4 bolt geometry already has its own weights. Empty release needs a
  # closing stroke even though the reference HK416 CAMARA track is static here.
  if clip=='reload_empty':travel=.035*(1-smooth((t-130/60)/(.065)))
  elif clip=='equip_charge':
   h=src['ARMA'].inverted()@src['PALANCAARGA'];h0=srcidle['ARMA'].inverted()@srcidle['PALANCAARGA'];travel=(h.translation-h0.translation).length
  else:travel=0
  p['WPN_bolt'].translation+=root.to_3x3()@Vector((0,travel,0))
  if clip=='equip_charge':p['WPN_ChargingHandle'].translation+=root.to_3x3()@Vector((0,travel,0))
  if clip=='reload_empty':
   current=src['ARMA'].inverted()@src['PALANCA'];reference=srcidle['ARMA'].inverted()@srcidle['PALANCA']
   angle=current.to_quaternion().rotation_difference(reference.to_quaternion()).angle*.5
   p['WPN_BoltCatch']=p['WPN_BoltCatch']@Quaternion(Vector((0,1,0)),angle).to_matrix().to_4x4()
  for side,longside in [('l','Left'),('r','Right')]:
   prefix='mixamorig2_'+longside
   un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
   shoulder=mapped_point(src,prefix+'Arm',un,gq)
   wrist=mapped_point(src,prefix+'Hand',hn,gq)
   if side=='l' and clip=='reload_empty':
    # The larger glove's outer finger edge meets this M4's actual bolt catch.
    wrist+=root.to_3x3()@Vector((-.018,-.014,0))*window(t,1.95,2.15,2.20,2.40)
   elbow_hint=mapped_point(src,prefix+'ForeArm',fn,gq)
   l1=(base[fn].translation-base[un].translation).length;l2=(base[hn].translation-base[fn].translation).length
   direction=wrist-shoulder;distance=direction.length;maxreach=max(maxreach,max(0,distance-l1-l2)*100)
   # Move the clavicle/shoulder naturally if the source reach exceeds this rig.
   if distance>l1+l2-.00001:shoulder+=direction.normalized()*(distance-l1-l2+.00001)
   axis=(wrist-shoulder).normalized();distance=(wrist-shoulder).length
   pole=elbow_hint-shoulder;pole-=axis*pole.dot(axis)
   if pole.length<.00001:pole=Vector((0,0,-1)).cross(axis)
   pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-along*along));elbow=shoulder+axis*along+pole*height
   uq=rotation(src,prefix+'Arm',un);fq=rotation(src,prefix+'ForeArm',fn)
   oldupper=base[un].to_quaternion().inverted()@(base[fn].translation-base[un].translation)
   oldfore=base[fn].to_quaternion().inverted()@(base[hn].translation-base[fn].translation)
   uq=(uq@oldupper).rotation_difference(elbow-shoulder)@uq
   fq=(fq@oldfore).rotation_difference(wrist-elbow)@fq
   p[un]=Matrix.LocRotScale(shoulder,uq,base[un].to_scale());p[fn]=Matrix.LocRotScale(elbow,fq,base[fn].to_scale())
   p[hn]=Matrix.LocRotScale(wrist,rotation(src,prefix+'Hand',hn),base[hn].to_scale())
   maxerr=max(maxerr,abs((elbow-shoulder).length-l1)*100,abs((wrist-elbow).length-l2)*100)
   for n in names:
    if (n.startswith('upperarm_twist') or n.startswith('lowerarm_twist')) and n.endswith('_'+side):p[n]=p[parents[n]]@local[n]
   for finger,title in [('thumb','Thumb'),('index','Index'),('middle','Middle'),('ring','Ring'),('pinky','Pinky')]:
    meta=finger+'_metacarpal_'+side
    if meta in p:p[meta]=p[hn]@local[meta]
    for j in range(1,4):
     n=f'{finger}_{j:02}_{side}';parent=parents[n]
     pos=(p[parent]@local[n]).translation
     sn=prefix+'Hand'+title+str(j);sp=prefix+'Hand'+(title+str(j-1) if j>1 else '')
     source_local=src[sp].to_quaternion().inverted()@src[sn].to_quaternion()
     source_local_idle=srcidle[sp].to_quaternion().inverted()@srcidle[sn].to_quaternion()
     axes=base[parent].to_quaternion().inverted()@handmap[side]@srcidle[sp].to_quaternion()
     lq=axes@source_local@source_local_idle.inverted()@axes.inverted()@local[n].to_quaternion()
     if side=='r' and finger=='index' and clip!='equip_charge' and j>1:
      lr=rest[parent].inverted()@rest[n]
      relaxed=lr.to_quaternion()@Quaternion(Vector((0,0,1)),math.radians(60 if j==2 else 20))
      lq=lq.slerp(relaxed,window(t,0,.15,data['clips'][clip]['duration']-.15,data['clips'][clip]['duration']))
     p[n]=Matrix.LocRotScale(pos,p[parent].to_quaternion()@lq,base[n].to_scale())
   if clip=='equip_charge' and side=='r':
    # Preserve the reference hook/roll, but constrain the two pulling fingers to
    # the actual M4 T handle for the contact and rearward stroke.
    pad=sum((p[n]@Vector((0,.010,0)) for n in ['index_03_r','middle_03_r']),Vector())*.5
    goal=root@Vector((-.009,.022+travel,.106))
    shift=(goal-pad)*window(t,.08,.20,.316667,.43)
    adjust_hand(p,side,shift,Quaternion())
   if clip=='reload_empty' and side=='l':
    # Fit from the deformed glove surface and rays against the actual M4 body,
    # not wrist/bone distance. See fit_release.py and release_fit.json.
    weight=window(t,1.95,2.15,2.20,2.40)
    rot=Quaternion().slerp(Euler((0,math.radians(-15),math.radians(-15))).to_quaternion(),weight)
    turn=root.to_quaternion()@rot@root.to_quaternion().inverted()
    adjust_hand(p,side,root.to_3x3()@Vector((.00097735,-.01916988,.00516653))*weight,turn)
  if clip=='equip_charge':
   # M4's longer rear assembly needs room for the hook. Extend forward along
   # the viewing axis during the stroke, retaining the lateral hip anchor.
   reach=Vector((0,.06,0))*window(t,0,.12,.40,.62)
   for n in names:p[n].translation+=reach
  samples.append(p)
 a=bpy.data.actions.new('M4_HK416_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for i,poses in enumerate(samples):
  for n in names:
   parent=parents[n];lr=rest[parent].inverted()@rest[n] if parent else rest[n];lp=poses[parent].inverted()@poses[n] if parent else poses[n]
   loc,q,scale=(lr.inverted()@lp).decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=i)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=len(samples)-1
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(OUT/f'A_M4_HK416_{clip}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 cache[clip]=samples;report['clips'][clip]={'duration':(len(samples)-1)/60,'samples':len(samples),'limb_length_error_cm':maxerr,'shoulder_reach_adaptation_cm':maxreach}
 # Read back every baked bone rather than assuming writing keys preserved it.
 set_action(a);err=0
 for i,poses in enumerate(samples):
  frame(i)
  for n in names:err=max(err,(r.pose.bones[n].matrix.translation-poses[n].translation).length*100)
 report['clips'][clip]['bake_error_cm']=err;assert err<.01,(clip,err)
 print('CLIP_COMPLETE',clip,report['clips'][clip],flush=True)
r.animation_data_clear()
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');r.select_set(True)
for o in r.children:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_M4_FoldingSights_HK416.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,mesh_smooth_type='FACE')
report['charging_handle_vertices']=len(handleids)
report['bolt_catch_vertices']=len(catchids)
report['fit_notes']={'equip_forward_clearance_cm':6,'empty_glove_rotation_deg':[0,-15,-15],'source_equip_seconds':.62,'original_bones_preserved':98}
set_action(bpy.data.actions['M4_HK416_reload_empty']);frame(130)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_HK416_Adapted_Editable.blend'))
(OUT/'build_report.json').write_text(json.dumps(report,indent=2))
# First-person and side contact sheets from the actual skinned target mesh.
for o in s.objects:
 if o.type=='MESH':o.hide_render=o.parent!=r
 if o.type=='LIGHT':o.hide_render=True
s.world.color=(.12,.12,.12)
camdata=bpy.data.cameras.new('ReplicaPreview');cam=bpy.data.objects.new('ReplicaPreview',camdata);s.collection.objects.link(cam);s.camera=cam
camdata.lens_unit='FOV';camdata.angle=math.radians(100);camdata.clip_start=.005
for i,pos in enumerate([(-.6,-.2,.8),(.6,.5,.6)]):
 ld=bpy.data.lights.new('ReplicaLight','AREA');ld.energy=65;ld.size=1;ob=bpy.data.objects.new('ReplicaLight',ld);s.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,.2,-.1))-ob.location).to_track_quat('-Z','Y').to_euler()
s.render.engine='BLENDER_EEVEE';s.render.resolution_x=960;s.render.resolution_y=540;s.render.resolution_percentage=100
for clip,indices in [('reload',[0,29,50,76,95,113,126]),('reload_empty',[0,21,40,54,80,100,115,130,142,162]),('equip_charge',[0,9,15,22,30,38])]:
 set_action(bpy.data.actions['M4_HK416_'+clip])
 for i in indices:
  frame(i);cam.location=(-.07,-.10,.07);cam.rotation_euler=(math.pi/2,0,0)
  folder=OUT/'Preview'/clip;folder.mkdir(parents=True,exist_ok=True);s.render.filepath=str(folder/f'{i:03}.png');bpy.ops.render.render(write_still=True)
print('REPLICA_BUILD_COMPLETE',report,flush=True)
