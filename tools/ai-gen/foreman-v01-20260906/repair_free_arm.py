"""Refine only Attack left arm; input is the validated whip v02 source."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'foreman-whip-v02.blend'))
a=bpy.data.objects['ForemanRig'];s=bpy.context.scene;act=bpy.data.actions['Attack'];a.animation_data.action=act
names=['upper_arm.L','forearm.L','hand.L'];rest={n:a.data.bones[n].matrix_local.copy() for n in names};length={n:a.data.bones[n].length for n in names}
times=sorted(set([i/80 for i in range(121)]+[.59625]));baseline={}
for t in times:
 s.frame_set(int(t*80),subframe=t*80-int(t*80));bpy.context.view_layer.update();baseline[t]={n:a.pose.bones[n].matrix.copy() for n in names}
for slot in act.slots:
 for layer in act.layers:
  for strip in layer.strips:
   bag=strip.channelbag(slot)
   if bag:
    for fc in list(bag.fcurves):
     if any('pose.bones["'+n+'"]' in fc.data_path for n in names):bag.fcurves.remove(fc)
keys=[(0,(.17,-.07,-.72)),(.18,(.26,-.19,-.53)),(.40,(.40,-.28,-.32)),(.59625,(.30,.13,-.46)),(.78,(.25,.10,-.51)),(1.10,(.19,-.05,-.65)),(1.5,(.17,-.07,-.72))]
def sample(t):
 for (ta,va),(tb,vb) in zip(keys,keys[1:]):
  if t<=tb:
   u=max(0,min(1,(t-ta)/(tb-ta)));u=u*u*(3-2*u);return Vector(va).lerp(Vector(vb),u)
 return Vector(keys[-1][1])
def orient(n,h,tail):
 b=a.data.bones[n];q=(b.tail_local-b.head_local).rotation_difference(tail-h)@rest[n].to_quaternion();m=q.to_matrix().to_4x4();m.translation=h;a.pose.bones[n].matrix=m;bpy.context.view_layer.update()
previous={};report={'modified_clip':'Attack','modified_bones':names,'samples':len(times),'max_wrist_step_m':0.}
last=None
for t in times:
 s.frame_set(int(t*80),subframe=t*80-int(t*80));bpy.context.view_layer.update()
 shoulder=a.pose.bones['clavicle.L'].tail.copy()
 chest=(a.pose.bones['chest'].matrix@a.data.bones['chest'].matrix_local.inverted()).to_3x3().normalized()
 weight=min(1,t/.14,(1.5-t)/.24);weight=max(0,weight);weight=weight*weight*(3-2*weight)
 old_wrist=baseline[t]['hand.L'].translation
 target=old_wrist.lerp(shoulder+chest@sample(t),weight)
 d=target-shoulder;l1=length[names[0]];l2=length[names[1]];dist=min(d.length,l1+l2-.001);u=d.normalized()
 pole=chest@Vector((.65,.35,-.15));v=(pole-u*pole.dot(u)).normalized();along=(l1*l1-l2*l2+dist*dist)/(2*dist)
 elbow=shoulder+u*along+v*math.sqrt(max(0,l1*l1-along*along));wrist=shoulder+u*dist
 orient(names[0],shoulder,elbow);orient(names[1],elbow,wrist)
 relaxed=((wrist-elbow).normalized()*.8+chest@Vector((0,-.12,-.20))).normalized()
 olddir=baseline[t]['hand.L'].to_3x3()@Vector((0,1,0));direction=olddir.lerp(relaxed,weight).normalized()
 orient(names[2],wrist,wrist+direction*length[names[2]])
 if t in [0,1.5]:
  for n in names:a.pose.bones[n].matrix=baseline[t][n];bpy.context.view_layer.update()
 for n in names:
  pb=a.pose.bones[n]
  if n in previous and pb.rotation_quaternion.dot(previous[n])<0:pb.rotation_quaternion.negate()
  previous[n]=pb.rotation_quaternion.copy()
  for c in ['location','rotation_quaternion','scale']:pb.keyframe_insert(c,frame=t*80,group=n)
 if last is not None:report['max_wrist_step_m']=max(report['max_wrist_step_m'],(wrist-last).length)
 last=wrist.copy()
for slot in act.slots:
 for layer in act.layers:
  for strip in layer.strips:
   bag=strip.channelbag(slot)
   if bag:
    for fc in bag.fcurves:
     if any('pose.bones["'+n+'"]' in fc.data_path for n in names):
      for k in fc.keyframe_points:k.interpolation='LINEAR'
a.animation_data.action=bpy.data.actions['Idle'];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-arm-v03.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [a,bpy.data.objects['Whip'],bpy.data.objects['ForemanBody']]:o.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'foreman-arm-v03.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
(R/'free-arm-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
