"""Compare controlled joint bends with the V07 baseline; save real renders."""
import bpy, bmesh, math, json, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parent
report={}
for version,path in [('V07',R.parent/'foreman-downstroke-v07-20260906/foreman-downstroke-v07.blend'),('V08',R/'foreman-retopo-v08.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(path))
 a=bpy.data.objects['ForemanRig'];body=bpy.data.objects['ForemanBody'];s=bpy.context.scene
 a.animation_data.action=None
 for tr in a.animation_data.nla_tracks:tr.mute=True
 for o in s.objects:
  if o.type=='MESH' and o!=body:o.hide_render=True
 s.render.engine='CYCLES';s.cycles.samples=12;s.render.resolution_x=760;s.render.resolution_y=760;s.render.resolution_percentage=100
 cam=s.camera;cam.data.ortho_scale=1.9
 coords=np.array([v.co[:] for v in body.data.vertices]);edges=np.array([e.vertices[:] for e in body.data.edges]);length=np.linalg.norm(coords[edges[:,0]]-coords[edges[:,1]],axis=1)
 mid=(coords[edges[:,0]]+coords[edges[:,1]])*.5
 mask=(mid[:,0]<-.35)&(mid[:,2]>1.38)&(mid[:,2]<2.2)&(length>.008)
 if version=='V07':
  common_edges=edges.copy();common_mask=mask.copy();source_coords=coords.copy()
 else:
  assert np.max(np.abs(coords[:len(source_coords),1:]-source_coords[:,1:]))<1e-6
  assert np.max(np.abs(coords[:len(source_coords),0]-source_coords[:,0]))<.02401
 common_length=np.linalg.norm(coords[common_edges[:,0]]-coords[common_edges[:,1]],axis=1)
 core=(np.abs(coords[:,0])<.56)&(coords[:,2]>1.28)&(coords[:,2]<1.85)&(coords[:,1]<-.20)
 report[version]={}
 for name,bone,angle in [('rest',None,0),('shoulder90','upper_arm.R',math.pi/2),('elbow90','forearm.R',math.pi/2)]:
  for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
  if bone:
   pb=a.pose.bones[bone];pb.rotation_mode='XYZ';pb.rotation_euler.x=angle
  bpy.context.view_layer.update()
  for helper,target,parent,factor in [('shoulder_support.R','upper_arm.R','clavicle.R',.55),('elbow_support.R','forearm.R','upper_arm.R',.5)]:
   if helper not in a.pose.bones:continue
   baseline=a.pose.bones[parent].matrix@a.data.bones[parent].matrix_local.inverted()@a.data.bones[target].matrix_local
   tm=a.pose.bones[target].matrix;m=baseline.to_quaternion().slerp(tm.to_quaternion(),factor).to_matrix().to_4x4();m.translation=tm.translation;a.pose.bones[helper].matrix=m
  bpy.context.view_layer.update()
  ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();p=np.array([v.co[:] for v in mesh.vertices]);ev.to_mesh_clear()
  ratios=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1)/np.maximum(length,1e-8)
  report[version][name]={'edge_stretch_p99':float(np.percentile(ratios[mask],99)),'fraction_edges_over_3x':float(np.mean(ratios[mask]>3)),'front_apron_max_displacement_m':float(np.max(np.linalg.norm(p[core]-coords[core],axis=1)))}
  common_ratio=np.linalg.norm(p[common_edges[:,0]]-p[common_edges[:,1]],axis=1)/np.maximum(common_length,1e-8)
  report[version][name]['same_source_edges_p99']=float(np.percentile(common_ratio[common_mask],99))
  report[version][name]['same_source_edges_over_3x']=int(np.sum(common_ratio[common_mask]>3))
  if '--metrics-only' in sys.argv:continue
  target=Vector((-.47,-.05,1.88));cam.location=target+Vector((-.5,-5,.2));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(R/f'{version}-{name}.png');bpy.ops.render.render(write_still=True)
  if name=='rest':
   mat=bpy.data.materials.new('Joint contour audit');mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.9
   wire=mat.node_tree.nodes.new('ShaderNodeWireframe');wire.inputs['Size'].default_value=.0009;mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.7,.7,.7,1);mix.inputs[2].default_value=(.03,.03,.03,1);mat.node_tree.links.new(wire.outputs[0],mix.inputs[0]);mat.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
   original=list(body.data.materials);body.data.materials.clear();body.data.materials.append(mat);s.render.filepath=str(R/f'{version}-topology.png');bpy.ops.render.render(write_still=True);body.data.materials.clear()
   for m in original:body.data.materials.append(m)
(R/'deformation-audit.json').write_text(json.dumps(report,indent=2));print('DEFORMATION_AUDIT',json.dumps(report))
