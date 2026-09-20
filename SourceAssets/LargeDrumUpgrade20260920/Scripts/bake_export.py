"""Bake each actual shell finish to an atlas and export in the original asset frame."""
import bpy,json,sys,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parents[1]
guns=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['M4','AKM','QBZ191']
frames=json.loads((O/'Reference/author_frames.json').read_text())
inputs=json.loads((O/'Reference/current_assets.json').read_text())
bpy.context.preferences.filepaths.save_version=0
for gun in guns:
 folder=O/gun;texdir=folder/'Textures';texdir.mkdir(exist_ok=True)
 bpy.ops.wm.open_mainfile(filepath=str(folder/'Drum_Construction.blend'))
 objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
 high=bpy.context.object;high.name='Drum_SurfaceMaster'
 high.data.calc_loop_triangles();count=len(high.data.loop_triangles)
 # Keep the interface and silhouette unaltered. The modeled shell is already
 # within the first-person geometry budget; LOD reduction is done in UE.
 low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low)
 low.name='SM_'+gun+'_LargeDrum_Upgrade'
 slot_ids=[int(m.get('drum_slot',0)) for m in high.data.materials]
 old_indices=[slot_ids[p.material_index] for p in low.data.polygons]
 low.data.materials.clear();mats=[];targets=[]
 for slot in inputs[gun]['slots']:
  m=bpy.data.materials.new(slot['slot']);m.use_nodes=True;low.data.materials.append(m);mats.append(m)
  t=m.node_tree.nodes.new('ShaderNodeTexImage');m.node_tree.nodes.active=t;targets.append(t)
 for p,i in zip(low.data.polygons,old_indices):p.material_index=i
 bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
 tri=low.modifiers.new('Explicit export triangles','TRIANGULATE');tri.keep_custom_normals=True
 bpy.ops.object.modifier_apply(modifier=tri.name)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
 bpy.ops.uv.smart_project(angle_limit=1.13446,island_margin=.009,area_weight=.15)
 bpy.ops.object.mode_set(mode='OBJECT');low.data.uv_layers.active.name='DrumSurfaceUV'
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
 scene.render.threads_mode='FIXED';scene.render.threads=8
 scene.render.bake.use_selected_to_active=True;scene.render.bake.use_clear=True
 scene.render.bake.margin=12;scene.render.bake.cage_extrusion=.00035;scene.render.bake.max_ray_distance=.0010
 scene.render.bake.normal_space='TANGENT'
 images={}
 for key,channel in [('BaseColor','Base Color'),('Roughness','Roughness'),('Metallic','Metallic'),('Normal',None)]:
  im=bpy.data.images.new('T_'+gun+'_Drum_'+key,width=2048,height=2048,alpha=False)
  im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
  for target in targets:target.image=im
  restore=[]
  if channel:
   for m in high.data.materials:
    n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
    prior=out.inputs['Surface'].links[0].from_socket;e=n.new('ShaderNodeEmission');sock=bs.inputs[channel]
    if sock.is_linked:l.new(sock.links[0].from_socket,e.inputs['Color'])
    else:
     v=sock.default_value;e.inputs['Color'].default_value=tuple(v) if channel=='Base Color' else (v,v,v,1)
    l.new(e.outputs['Emission'],out.inputs['Surface']);restore.append((m,prior,out,e))
  bpy.ops.object.select_all(action='DESELECT');high.hide_render=False;high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
  print('BAKING',gun,key,flush=True)
  try:bpy.ops.object.bake(type='EMIT' if channel else 'NORMAL')
  finally:
   for m,prior,out,e in restore:m.node_tree.links.new(prior,out.inputs['Surface']);m.node_tree.nodes.remove(e)
  images[key]=im
  if key in ['BaseColor','Normal']:
   im.filepath_raw=str(texdir/(im.name+'.png'));im.file_format='PNG';im.save()
 rough=np.empty(2048*2048*4,dtype=np.float32);metal=rough.copy()
 images['Roughness'].pixels.foreach_get(rough);images['Metallic'].pixels.foreach_get(metal)
 data=np.ones((2048*2048,4),dtype=np.float32);data[:,1]=rough.reshape(-1,4)[:,0];data[:,2]=metal.reshape(-1,4)[:,0]
 mr=bpy.data.images.new('T_'+gun+'_Drum_MetalRough',width=2048,height=2048,alpha=False);mr.colorspace_settings.name='Non-Color'
 mr.pixels.foreach_set(data.ravel());mr.filepath_raw=str(texdir/(mr.name+'.png'));mr.file_format='PNG';mr.save()
 for m in mats:
  n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
  bc=n.new('ShaderNodeTexImage');bc.image=images['BaseColor'];l.new(bc.outputs['Color'],bs.inputs['Base Color'])
  t=n.new('ShaderNodeTexImage');t.image=mr;sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs['Color'])
  l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
  nt=n.new('ShaderNodeTexImage');nt.image=images['Normal'];norm=n.new('ShaderNodeNormalMap');norm.uv_map='DrumSurfaceUV'
  l.new(nt.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs['Normal'],bs.inputs['Normal'])
 high.hide_render=True;high.hide_set(True)
 bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Editable.blend'))
 low.data.transform(Matrix(frames[gun]['canonical_to_source']))
 bpy.ops.export_scene.fbx(filepath=str(O/'Export'/('SM_'+gun+'_LargeDrum_Upgrade.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Integrated.blend'))
 receipt={'gun':gun,'source_triangles':count,'export_triangles':count,'source':str(folder/'Drum_Editable.blend'),
 'fbx':str(O/'Export'/('SM_'+gun+'_LargeDrum_Upgrade.fbx')),'atlas_resolution':2048,
 'channels':'G roughness; B metallic; R unused white','normal':'OpenGL tangent; UE flips green once',
 'uv':'DrumSurfaceUV / UV0','material_slots':[m.name for m in mats],
 'canonical_to_source':frames[gun]['canonical_to_source'],'game_tested':False}
 (folder/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 print('DRUM_BAKE_EXPORT_COMPLETE',gun,count,flush=True)
