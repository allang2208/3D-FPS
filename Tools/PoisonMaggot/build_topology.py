import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
root=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911');out=root/'delivery';out.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'raw_source.blend'));bpy.context.preferences.view.language='en_US';bpy.context.preferences.view.use_translate_new_dataname=False
high=next(o for o in bpy.context.scene.objects if o.type=='MESH');high.name='PoisonMaggot_High'
bpy.context.view_layer.objects.active=high;high.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
coords=[v.co for v in high.data.vertices];lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)));factor=2.2/(hi.x-lo.x)
for v in high.data.vertices:v.co=(v.co-Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z)))*factor
bm=bmesh.new();bm.from_mesh(high.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002);bm.to_mesh(high.data);bm.free();high.data.update()
# Refine the same continuous frontal surface into a single recessed oral basin.
changed=0
for v in high.data.vertices:
 x,y,z=v.co;r=math.sqrt((y/.20)**2+((z-.29)/.15)**2)
 if x>.83 and r<1:
  w=(1-r*r)**2;v.co.x-=.075*w*min(1,(x-.83)/.12);changed+=1
high.data.update()
if high.data.has_custom_normals:
 bpy.ops.mesh.customdata_custom_splitnormals_clear()
mat=high.data.materials[0];mat.name='Maggot_SourcePBR';nt=mat.node_tree;nodes=nt.nodes;links=nt.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
print('SOURCE_NODES',[(n.name,n.type,n.image.name if n.type=='TEX_IMAGE' and n.image else '') for n in nodes],flush=True)
# Keep generated albedo, introduce measured-scale microtexture and organic roughness.
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=125;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7
ramp=nodes.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=0;ramp.inputs['From Max'].default_value=1;ramp.inputs['To Min'].default_value=.32;ramp.inputs['To Max'].default_value=.58
links.new(noise.outputs['Fac'],ramp.inputs['Value']);links.new(ramp.outputs['Result'],bs.inputs['Roughness'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.0012;links.new(noise.outputs['Fac'],bump.inputs['Height'])
if bs.inputs['Normal'].is_linked:links.new(bs.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
links.new(bump.outputs['Normal'],bs.inputs['Normal']);bs.inputs['Subsurface Weight'].default_value=.055;bs.inputs['Subsurface Radius'].default_value=(1,.55,.25);bs.inputs['Subsurface Scale'].default_value=.012
for p in high.data.polygons:p.use_smooth=True
# Independent quad reconstruction after welding UV split vertices. The untouched high source remains.
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='PoisonMaggot_Retopo'
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
pre=low.modifiers.new('QuadSolverPreparation','DECIMATE');pre.ratio=.24;bpy.ops.object.modifier_apply(modifier=pre.name)
print('QUADRIFLOW_START',len(low.data.polygons),flush=True)
bpy.ops.object.quadriflow_remesh(use_mesh_symmetry=False,use_preserve_sharp=False,use_preserve_boundary=False,mode='FACES',target_faces=22000,seed=17)
print('QUADRIFLOW_DONE',len(low.data.vertices),len(low.data.polygons),flush=True)
# Retain the sculpt silhouette and folds on the reconstructed connectivity.
sh=low.modifiers.new('ProjectToSource','SHRINKWRAP');sh.target=high;sh.wrap_method='NEAREST_SURFACEPOINT';sh.wrap_mode='ON_SURFACE';bpy.ops.object.modifier_apply(modifier=sh.name)
for p in low.data.polygons:p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
# Bake source colour and detailed tangent normals to new UVs (4k).
low.data.materials.clear();lm=bpy.data.materials.new('Maggot_PBR');lm.use_nodes=True;low.data.materials.append(lm);ln=lm.node_tree.nodes;lb=next(n for n in ln if n.type=='BSDF_PRINCIPLED');ll=lm.node_tree.links
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.render.bake.use_selected_to_active=True;s.render.bake.cage_extrusion=.055;s.render.bake.max_ray_distance=.11;s.render.bake.margin=16
high.hide_render=False
maps={}
for sem in ['BaseColor','Normal','Roughness']:
 im=bpy.data.images.new('T_Maggot_'+sem,width=4096,height=4096,alpha=False);im.colorspace_settings.name='sRGB' if sem=='BaseColor' else 'Non-Color';n=ln.new('ShaderNodeTexImage');n.image=im;ln.active=n
 bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
 if sem=='BaseColor':s.render.bake.use_pass_direct=False;s.render.bake.use_pass_indirect=False;s.render.bake.use_pass_color=True;bpy.ops.object.bake(type='DIFFUSE')
 else:bpy.ops.object.bake(type='NORMAL' if sem=='Normal' else 'ROUGHNESS')
 im.filepath_raw=str(out/('T_Maggot_'+sem+'.png'));im.file_format='PNG';im.save();maps[sem]=n
 print('BAKE_DONE',sem,flush=True)
ll.new(maps['BaseColor'].outputs['Color'],lb.inputs['Base Color']);ll.new(maps['Roughness'].outputs['Color'],lb.inputs['Roughness']);normal=ln.new('ShaderNodeNormalMap');ll.new(maps['Normal'].outputs['Color'],normal.inputs['Color']);ll.new(normal.outputs['Normal'],lb.inputs['Normal']);lb.inputs['Subsurface Weight'].default_value=.045;lb.inputs['Subsurface Scale'].default_value=.012
high.hide_render=True;high.hide_set(True)
report={'high_vertices':len(high.data.vertices),'low_vertices':len(low.data.vertices),'low_faces':len(low.data.polygons),'quads':sum(len(p.vertices)==4 for p in low.data.polygons),'mouth_vertices_refined':changed,'length_m':2.2,'method':'weld, quadriflow, shrinkwrap, UV unwrap, high-to-low 4k PBR bake','maps':{k:n.image.filepath for k,n in maps.items()}}
(out/'topology.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(out/'PoisonMaggot_Retopology.blend'));print('MAGGOT_TOPOLOGY_COMPLETE',json.dumps(report),flush=True)
