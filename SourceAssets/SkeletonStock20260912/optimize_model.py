"""Derivative of the real Hunyuan mesh: weld, size, simplify and bake; raw stays intact."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'skeleton_raw.glb'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.name='Hunyuan_High_Reference';bpy.context.view_layer.update();bpy.context.view_layer.objects.active=high;high.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=Vector([min(v.co[i] for v in high.data.vertices) for i in range(3)]);hi=Vector([max(v.co[i] for v in high.data.vertices) for i in range(3)]);span=hi-lo
# Correct the generated tall silhouette to the reviewed legacy game proportions.
target=Vector((23,4.8,12.6));scale=Vector([target[i]/span[i] for i in range(3)])
for v in high.data.vertices:v.co=Vector(((v.co.x-lo.x)*scale.x,(v.co.y-(lo.y+hi.y)/2)*scale.y,(v.co.z-hi.z)*scale.z+1.8))
bm=bmesh.new();bm.from_mesh(high.data);rawverts=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0002);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));welded=len(bm.verts);bm.to_mesh(high.data);bm.free()
original=high.data.materials[0];base=original.node_tree.nodes.get('Principled BSDF');original_images=[n.image.name for n in original.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
def mat(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=175;noise.inputs['Detail'].default_value=2
 ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.86 for c in color),1);ramp.color_ramp.elements[1].color=(*(c*1.12 for c in color),1);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
 bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.006;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
 return m
frame=mat('Graphite_Frame',(.045,.053,.061),.8,.48);polymer=mat('Charcoal_Cheek',(.034,.033,.030),0,.7);rubber=mat('Rubber_Pad',(.012,.015,.018),0,.86)
high.data.materials.clear()
for m in [frame,polymer,rubber]:high.data.materials.append(m)
for f in high.data.polygons:
 c=f.center;f.material_index=2 if c.x>21.6 else 1 if 7.3<c.x<18.7 and c.z>.32 else 0;f.use_smooth=True
low=high.copy();low.data=high.data.copy();low.name='SM_SkeletonStock';bpy.context.collection.objects.link(low)
bpy.context.view_layer.objects.active=low;high.select_set(False);low.select_set(True)
dec=low.modifiers.new('Runtime triangle budget','DECIMATE');dec.ratio=18000/len(low.data.polygons);bpy.ops.object.modifier_apply(modifier=dec.name)
bm=bmesh.new();bm.from_mesh(low.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(low.data);bm.free()
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(62),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=10;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.09;s.render.bake.max_ray_distance=.24
# Separate destination materials prevent circular baking dependencies on the high mesh.
dest=bpy.data.materials.new('SkeletonStock_PBR');dest.use_nodes=True;low.data.materials.clear();low.data.materials.append(dest)
for f in low.data.polygons:f.material_index=0
maps={};high.select_set(True)
for channel in ['BaseColor','Roughness','Metallic','Normal']:
 img=bpy.data.images.new('T_SkeletonStock_'+channel,2048,2048,alpha=False)
 if channel!='BaseColor':img.colorspace_settings.name='Non-Color'
 node=dest.node_tree.nodes.new('ShaderNodeTexImage');node.image=img;dest.node_tree.nodes.active=node;saved=[]
 if channel!='Normal':
  for m in [frame,polymer,rubber]:
   n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF');socket=bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]];em=n.new('ShaderNodeEmission')
   if socket.is_linked:l.new(socket.links[0].from_socket,em.inputs[0])
   else:
    val=socket.default_value;em.inputs[0].default_value=tuple(val) if channel=='BaseColor' else (val,val,val,1)
   l.new(em.outputs[0],n.get('Material Output').inputs['Surface']);saved.append((m,em))
 bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT');img.filepath_raw=str(P/(img.name+'.png'));img.file_format='PNG';img.save();maps[channel]=img
 for m,em in saved:m.node_tree.links.new(m.node_tree.nodes.get('Principled BSDF').outputs[0],m.node_tree.nodes.get('Material Output').inputs['Surface']);m.node_tree.nodes.remove(em)
high.select_set(False);high.hide_render=True;high.hide_set(True)
bs=dest.node_tree.nodes.get('Principled BSDF')
for channel,img in maps.items():
 n=next(n for n in dest.node_tree.nodes if n.type=='TEX_IMAGE' and n.image==img)
 if channel=='Normal':
  norm=dest.node_tree.nodes.new('ShaderNodeNormalMap');dest.node_tree.links.new(n.outputs[0],norm.inputs['Color']);dest.node_tree.links.new(norm.outputs[0],bs.inputs['Normal'])
 else:dest.node_tree.links.new(n.outputs[0],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
low.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(low.data)
report={'source':'skeleton_raw.glb','method':'weld and decimate actual generated geometry; silhouette height calibrated to legacy proportions; authored PBR rebaked','raw_triangles':500000,'raw_vertices':rawverts,'welded_vertices':welded,'triangles':len(low.data.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'dimensions_cm':list(target),'generated_bounds':list(span),'original_images':original_images,'uv_layers':len(low.data.uv_layers),'material_slots':len(low.data.materials)};bm.free()
assert report['triangles']<19000 and report['degenerate_faces']==0
(P/'mesh_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.export_scene.fbx(filepath=str(P/'SM_SkeletonStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False)
# glTF uses metres; FBX above imports as centimetres.
low.scale=(.01,)*3;bpy.ops.export_scene.gltf(filepath=str(P/'SkeletonStock.glb'),use_selection=True,export_apply=True);low.scale=(1,)*3
s.world=bpy.data.worlds.new('StockStudio');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.11,.13,.16,1)
center=Vector((11.5,0,-4));
def aim(o):o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
for pos,power,size in [((2,-15,22),2300,14),((20,15,12),3200,12),((27,-7,5),1500,10)]:
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=size;aim(o)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=29;s.camera=cam;s.render.resolution_x=1100;s.render.resolution_y=750;s.render.resolution_percentage=100;s.cycles.samples=32;s.cycles.use_denoising=True;s.render.bake.use_selected_to_active=False
for name,pos in [('beauty',(30,-30,13)),('side',(11.5,-35,-4)),('rear',(36,-6,2))]:
 cam.location=pos;aim(cam);s.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low;bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_Editable.blend'));print('SKELETON_MODEL_PASS',json.dumps(report))
