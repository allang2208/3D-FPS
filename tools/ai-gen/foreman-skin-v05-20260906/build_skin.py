"""Localized, topology-connected shoulder/elbow relaxation and finger cup controls.
Keeps the V04 body, UVs, all existing bone rests and business animation timing.
"""
import bpy, math, json
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-motion-v04-20260906/foreman-motion-v04.blend'))
a=bpy.data.objects['ForemanRig']; body=bpy.data.objects['ForemanBody']; s=bpy.context.scene
a.animation_data.action=None
for tr in a.animation_data.nla_tracks: tr.mute=True
for pb in a.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
names=list(body.vertex_groups.keys()); coords=np.array([v.co[:] for v in body.data.vertices]); original=np.zeros((len(coords),len(names)))
for v in body.data.vertices:
 for g in v.groups: original[v.index,g.group]=g.weight
edges=np.array([e.vertices[:] for e in body.data.edges]); src=np.concatenate([edges[:,0],edges[:,1]]); dst=np.concatenate([edges[:,1],edges[:,0]])
distance=np.linalg.norm(coords[src]-coords[dst],axis=1); conductance=1/np.maximum(distance,.008)
denom=np.bincount(src,weights=conductance,minlength=len(coords))
# Smooth over mesh neighbours, never across spatially adjacent disconnected surfaces.
def smoothstep(a,b,x):
 u=np.clip((x-a)/(b-a),0,1); return u*u*(3-2*u)
x=np.abs(coords[:,0]);z=coords[:,2]
mask=smoothstep(.33,.48,x)*(1-smoothstep(.85,1.0,x))*smoothstep(1.25,1.42,z)*(1-smoothstep(2.08,2.23,z))
w=original.copy()
for iteration in range(65):
 avg=np.stack([np.bincount(src,weights=conductance*w[dst,k],minlength=len(coords))/np.maximum(denom,1e-12) for k in range(len(names))],axis=1)
 w+=.60*mask[:,None]*(avg-w)
# glTF four-influence contract; normalize after pruning.
order=np.argsort(w,axis=1)[:,:-4];np.put_along_axis(w,order,0,axis=1);w/=w.sum(axis=1)[:,None]
def assign(weights):
 for g in body.vertex_groups:g.remove(list(range(len(coords))))
 for k,g in enumerate(body.vertex_groups):
  for i in np.where(weights[:,k]>1e-7)[0]:g.add([int(i)],float(weights[i,k]),'REPLACE')
def deformation_metric():
 for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 pb=a.pose.bones['upper_arm.R'];pb.rotation_mode='XYZ';pb.rotation_euler.x=math.pi/2;bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:] for v in me.vertices]);ev.to_mesh_clear()
 restlen=np.linalg.norm(coords[edges[:,0]]-coords[edges[:,1]],axis=1); posedlen=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)
 selected=(mask[edges[:,0]]>.2)&(restlen>.008)
 return {'edge_stretch_p99':float(np.percentile((posedlen/restlen)[selected],99)), 'edges_over_3x':int(np.sum((posedlen/restlen)[selected]>3))}
report={'before':deformation_metric()};assign(w);report['after']=deformation_metric()
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.objects.active=a;bpy.ops.object.mode_set(mode='EDIT')
for side,sign in [('L',1),('R',-1)]:
 b=a.data.edit_bones.new('fingers_cup.'+side);b.head=(sign*.875,-.025,1.13);b.tail=(sign*.90,-.025,1.01);b.parent=a.data.edit_bones['hand.'+side]
bpy.ops.object.mode_set(mode='OBJECT')
for side,sign in [('L',1),('R',-1)]:
 group=body.vertex_groups.new(name='fingers_cup.'+side);hand=body.vertex_groups['hand.'+side]
 for i in range(len(coords)):
  if coords[i,0]*sign<.79:continue
  amount=float((1-smoothstep(1.075,1.16,coords[i,2]))*smoothstep(.79,.84,abs(coords[i,0]))*w[i,names.index(hand.name)])
  if amount>1e-6:
   group.add([i],amount,'REPLACE');hand.add([i],max(0,float(w[i,names.index(hand.name)])-amount),'REPLACE')
 # Use anatomical inward curl in the new bone's rest frame.
 axis=a.data.bones[group.name].matrix_local.to_3x3().inverted()@Vector((0,sign,0))
 for act in bpy.data.actions:
  a.animation_data.action=act
  duration={'Idle':1,'Walk':1.5,'Attack':1.5,'Death':1.4,'Howl':3}.get(act.name)
  if duration is None:continue
  for frame in range(round(duration*s.render.fps)+1):
   t=frame/s.render.fps
   amount=.48 if side=='R' else .16
   if act.name=='Attack':amount+=(.10 if side=='R' else -.10)*math.sin(math.pi*t/duration)**2
   if act.name=='Death':amount*=1-.7*smoothstep(.65,1.3,t)
   pb=a.pose.bones[group.name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(axis,amount);pb.keyframe_insert('rotation_quaternion',frame=frame,group=group.name)
report['finger_controls']=['fingers_cup.L','fingers_cup.R'];report['scope']='Grouped four-finger curl; thumb and individual phalanges remain source geometry.'
for v in body.data.vertices:
 influences=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-7],key=lambda x:-x[1])
 total=sum(weight for _,weight in influences[:4])
 for index,weight in influences:
  body.vertex_groups[index].remove([v.index])
 for index,weight in influences[:4]:body.vertex_groups[index].add([v.index],weight/total,'REPLACE')
for pb in a.pose.bones:
 pb.matrix_basis=Matrix.Identity(4);pb.rotation_mode='QUATERNION'
a.animation_data.action=bpy.data.actions['Idle'];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-skin-v05.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in [a,body,bpy.data.objects['Whip']]:o.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.export_scene.gltf(filepath=str(R/'foreman-skin-v05.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=True)
(R/'skin-report.json').write_text(json.dumps(report,indent=2));print('SKIN_V05',json.dumps(report))
