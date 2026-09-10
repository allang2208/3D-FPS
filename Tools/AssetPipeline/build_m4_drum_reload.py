import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'M4_Drum_Optimized.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];data=json.loads((OUT/'build.json').read_text())
G=Matrix(data['source_to_component']);center=Vector(data['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
report=[]
def set_action(a):
 r.animation_data_create();r.animation_data.action=a
 if len(a.slots):r.animation_data.action_slot=a.slots[0]
def frame(t):s.frame_set(int(t),subframe=t-int(t));bpy.context.view_layer.update()
for source_name,name,end in [('M4_reload_FingerCurl','A_M4_DrumReload',188),('M4_reload_empty_BoltRelease','A_M4_DrumReloadEmpty',228)]:
 source=bpy.data.actions[source_name];samples=[];max_push=0;changed=0;raw=[]
 for t in range(end+1):
  set_action(source);frame(t)
  drum=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
  inv=drum.inverted();wrist=r.pose.bones['hand_l'].matrix.copy();middle=r.pose.bones['middle_01_l'].head.copy()
  push=Vector()
  for point in [wrist.translation,wrist.translation.lerp(middle,.65),middle,*[r.pose.bones[n].tail for n in ['index_03_l','middle_03_l','ring_03_l','pinky_03_l']]]:
   p=inv@point;rad=Vector((p.x,0,p.z+.085))
   if abs(p.y)>.05 or p.z>-.034 or rad.length>.079:continue
   direction=rad.normalized() if rad.length>.001 else Vector((-1,0,0));delta=direction*.08-rad
   # Fade across the shell depth and upper shoulder; avoid a hard IK switch.
   weight=min(1,max(0,(.05-abs(p.y))/.015))*min(1,max(0,(-.034-p.z)/.018))
   delta*=weight
   if delta.length>push.length:push=delta
  raw.append(drum.to_3x3()@push)
 # Changes in the closest finger can switch the displacement direction. Filter
 # the correction, not the source animation, before solving the rigid arm chain.
 offsets=[]
 for t in range(end+1):
  weights=[(j,math.exp(-.5*((j-t)/5)**2)) for j in range(max(0,t-15),min(end,t+15)+1)]
  offsets.append(sum((raw[j]*w for j,w in weights),Vector())/sum(w for j,w in weights))
 for t,delta in enumerate(offsets):
  set_action(source);frame(t);wrist=r.pose.bones['hand_l'].matrix.copy()
  if delta.length>1e-6:
   changed+=1;max_push=max(max_push,delta.length)
   upper=r.pose.bones['upperarm_l'].matrix.copy();fore=r.pose.bones['lowerarm_l'].matrix.copy()
   a=upper.translation;b=fore.translation;c=wrist.translation;goal=c+delta
   l1=(b-a).length;l2=(c-b).length;direction=(goal-a).normalized();d=min((goal-a).length,l1+l2-1e-5);goal=a+direction*d
   pole=(b-a)-direction*(b-a).dot(direction);pole.normalize();along=(l1*l1-l2*l2+d*d)/(2*d)
   elbow=a+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
   r.pose.bones['upperarm_l'].matrix=Matrix.LocRotScale(a,(b-a).rotation_difference(elbow-a)@upper.to_quaternion(),upper.to_scale());bpy.context.view_layer.update()
   r.pose.bones['lowerarm_l'].matrix=Matrix.LocRotScale(elbow,(c-b).rotation_difference(goal-elbow)@fore.to_quaternion(),fore.to_scale());bpy.context.view_layer.update()
   wrist.translation=goal;r.pose.bones['hand_l'].matrix=wrist;bpy.context.view_layer.update()
  samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
 a=bpy.data.actions.new(name);a.use_fake_user=True;set_action(a);previous={}
 for t,poses in enumerate(samples):
  for n,m in poses.items():
   b=r.pose.bones[n];p,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b.rotation_mode='QUATERNION';b.location=p;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=t)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report.append(dict(clip=name,frames=end+1,duration=end/60,adjusted_frames=changed,max_hand_shift_cm=max_push*100))
 # Render actual fitted mesh and corrected source pose before game import.
 for o in s.objects:o.hide_render=o not in r.children
 for o in r.children:
  if 'Magazine' in o.name:o.hide_render=True
 focus=Vector((.05,.28,-.1));bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.65
 cam.location=focus+Vector((.65,-.22,.12));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
 for off in [(.5,0,.5),(-.4,.2,.2)]:
  bpy.ops.object.light_add(type='AREA',location=focus+Vector(off));bpy.context.object.data.energy=35;bpy.context.object.data.size=.6
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1100;s.render.resolution_y=750;s.render.resolution_percentage=100
 for t in [24,45,90,114,174]:
  frame(t);s.render.filepath=str(OUT/(name+'-'+str(t)+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_Drum_Reload_Editable.blend'))
(OUT/'reload-build.json').write_text(json.dumps(report,indent=2));print('M4_DRUM_RELOAD_BUILD_PASS',report)
