import bpy,bmesh,math,json
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob('reference_stock_high_textured_master*.glb'))))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');matrix=high.matrix_world.copy();pts=[matrix@v.co for v in high.data.vertices]
hi=max(p.x for p in pts);lo=min(p.x for p in pts);rim=[p for p in pts if p.x>hi-.018]
origin=Vector((hi,(max(p.y for p in rim)+min(p.y for p in rim))/2,(max(p.z for p in rim)+min(p.z for p in rim))/2))
scale=23.03/(hi-lo);rot=Matrix.Rotation(math.pi,4,'Z')
for v in high.data.vertices:v.co=rot@((matrix@v.co-origin)*scale)
high.matrix_world=Matrix.Identity(4);high.name='Generated_Textured_Master'
bm=bmesh.new();bm.from_mesh(high.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002);bm.to_mesh(high.data);bm.free()
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='SM_SkeletonStock'
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
low.data.calc_loop_triangles();m=low.modifiers.new('Preserve generated silhouette LOD0','DECIMATE');m.ratio=50000/len(low.data.loop_triangles);m.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=m.name)
low.data.materials[0]=high.data.materials[0].copy();mat=low.data.materials[0];mat.name='M_ReferenceStock5080';nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
base=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and n.outputs['Color'].is_linked and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
other=next(n.image for n in nt.nodes if n.type=='TEX_IMAGE' and n.image!=base)
for name,img in [('BaseColor',base),('MetalRough',other)]:img.filepath_raw=str(P/('T_ReferenceStock_'+name+'.png'));img.file_format='PNG';img.save()
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.012;s.render.bake.max_ray_distance=.04;s.render.bake.margin=8;s.render.bake.use_clear=False
normal=bpy.data.images.new('T_ReferenceStock_Normal',4096,4096);normal.colorspace_settings.name='Non-Color';normal.generated_color=(.5,.5,1.,1.);n=nt.nodes.new('ShaderNodeTexImage');n.image=normal;nt.nodes.active=n;high.select_set(True)
bpy.ops.object.bake(type='NORMAL')
import numpy as np
pixels=np.empty(len(normal.pixels),dtype=np.float32);normal.pixels.foreach_get(pixels);rgb=pixels.reshape((-1,4));invalid=rgb[:,2]<.5;rgb[invalid,:3]=(.5,.5,1.);normal.pixels.foreach_set(pixels);normal.update();normal.filepath_raw=str(P/'T_ReferenceStock_Normal.png');normal.file_format='PNG';normal.save()
nrm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],nrm.inputs['Color']);nt.links.new(nrm.outputs['Normal'],bs.inputs['Normal'])
high.hide_render=True;high.hide_set(True);high.select_set(False)
low.data.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(low.data)
report={'origin_generated':list(origin),'author_length_cm':23.03,'dimensions_cm':list(low.dimensions),'triangles':len(low.data.loop_triangles),'vertices':len(low.data.vertices),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'normal_bake_rejected_pixels':int(invalid.sum()),'normal_bake_pixels':len(rgb),'method':'decimate actual generated textured master; retain generated color and packed metallic/roughness; bake 4K normals from textured master'};bm.free()
assert 45000<report['triangles']<51000 and report['degenerate_faces']==0
(P/'game_mesh_report.json').write_text(json.dumps(report,indent=2))
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ReferenceStock5080_Game_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'SM_SkeletonStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
low.scale=(.01,)*3;bpy.ops.export_scene.gltf(filepath=str(P/'ReferenceStock5080_Game.glb'),use_selection=True,export_apply=True)
print('STOCK_GAME_MESH_PASS',json.dumps(report),flush=True)
