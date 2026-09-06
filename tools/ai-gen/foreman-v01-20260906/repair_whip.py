"""Repair only whip skin/animation; preserve every body animation channel.
Run after rig_and_animate.py. Independent output is foreman-whip-v02.glb/.blend.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'foreman-rigged.blend'))
scene=bpy.context.scene;arm=bpy.data.objects['ForemanRig'];whip=bpy.data.objects['Whip']
arm.animation_data.action=None
bpy.context.view_layer.objects.active=arm
bpy.ops.object.mode_set(mode='EDIT')
start=Vector((-.87,-.025,1.10))
# Each cross-section owns a rigid frame. Siblings never inherit segment scale
# or shear, which cannot be represented in glTF's TRS animation channels.
for i in range(33):
 n=f'whip.{i:02d}';b=arm.data.edit_bones.get(n) or arm.data.edit_bones.new(n)
 b.parent=arm.data.edit_bones['hand.R'];b.use_connect=False
 b.head=start+Vector((0,0,-i*.1));b.tail=b.head+Vector((0,0,-.1))
bpy.ops.object.mode_set(mode='OBJECT')
whip.vertex_groups.clear()
for i in range(33):
 g=whip.vertex_groups.new(name=f'whip.{i:02d}');g.add(list(range(i*8,i*8+8)),1,'REPLACE')
for p in whip.data.polygons:p.use_smooth=True
rest=arm.data.bones['hand.R'].matrix_local.copy()
grip=rest.inverted()@(arm.data.bones['hand.R'].head_local.lerp(arm.data.bones['hand.R'].tail_local,.65))
clips={'Idle':1.,'Walk':1.5,'Attack':1.5,'Howl':3.,'Death':1.4}
report={'reason':'hierarchical nonuniform scale produced unrepresentable shear and exploding intermediate frames','rig':'33 rigid cross-section bones, siblings of hand.R, unit scale','samples':0,'max_vertex_distance_from_grip':0.,'max_local_scale_error':0.}
for name,duration in clips.items():
 act=bpy.data.actions[name]
 for slot in act.slots:
  for layer in act.layers:
   for strip in layer.strips:
    bag=strip.channelbag(slot)
    if bag:
     for fc in list(bag.fcurves):
      if 'pose.bones["whip.' in fc.data_path:bag.fcurves.remove(fc)
 arm.animation_data.action=act
 for pb in arm.pose.bones:
  if pb.name.startswith('whip.'):pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
 previous={}
 times=sorted(set([i/80 for i in range(round(duration*80)+1)]+([.59625] if name=='Attack' else [])))
 for t in times:
  scene.frame_set(int(t*80),subframe=t*80-int(t*80));bpy.context.view_layer.update()
  anchor=arm.pose.bones['hand.R'].matrix@grip
  points=[]
  for i in range(33):
   u=i/32;ang=u*math.tau*2.15
   coil=anchor+Vector((.24*math.sin(ang),.05*u,-.24*(1-math.cos(ang))-.10*u))
   overhead=anchor+Vector((-.22*math.sin(u*math.pi),1.8*u,.7*math.sin(u*math.pi)))
   extended=anchor+Vector((.07*math.sin(u*math.tau),-2.7*u,-.65*u))
   v=coil
   if name=='Attack':
    if t<.45:v=coil.lerp(overhead,min(1,t/.4))
    elif t<.59625:v=overhead.lerp(extended,min(1,(t-.45)/.14625))
    elif t<.70:v=extended
    else:v=extended.lerp(coil,min(1,(t-.70)/.80))
   if name=='Death':v.z=max(.05,v.z)
   points.append(v)
  normal=Vector((0,1,0))
  for i in range(33):
   tangent=points[min(32,i+1)]-points[max(0,i-1)]
   if tangent.length<1e-6:tangent=Vector((0,0,-1))
   tangent.normalize()
   # Parallel transport the tube frame to avoid arbitrary axial flips.
   normal=normal-tangent*normal.dot(tangent)
   if normal.length<1e-5:normal=Vector((1,0,0))-tangent*tangent.x
   normal.normalize();z=normal.cross(tangent).normalized()
   mat=Matrix((normal,tangent,z)).transposed().to_4x4();mat.translation=points[i]
   pb=arm.pose.bones[f'whip.{i:02d}'];pb.matrix=mat
   if i in previous and pb.rotation_quaternion.dot(previous[i])<0:pb.rotation_quaternion.negate()
   previous[i]=pb.rotation_quaternion.copy()
   for c in ['location','rotation_quaternion','scale']:pb.keyframe_insert(c,frame=t*80,group=pb.name)
   report['max_local_scale_error']=max(report['max_local_scale_error'],max(abs(s-1) for s in pb.scale))
  bpy.context.view_layer.update()
  ev=whip.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
  far=max((v.co-anchor).length for v in m.vertices);ev.to_mesh_clear()
  assert far<3.5,(name,t,far)
  report['max_vertex_distance_from_grip']=max(report['max_vertex_distance_from_grip'],far);report['samples']+=1
 for slot in act.slots:
  for layer in act.layers:
   for strip in layer.strips:
    bag=strip.channelbag(slot)
    if bag:
     for fc in bag.fcurves:
      if 'pose.bones["whip.' in fc.data_path:
       for k in fc.keyframe_points:k.interpolation='LINEAR'
assert report['max_local_scale_error']<.0001,report
arm.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'foreman-whip-v02.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [arm,whip,bpy.data.objects['ForemanBody']]:o.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.export_scene.gltf(filepath=str(ROOT/'foreman-whip-v02.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
(ROOT/'whip-repair-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
