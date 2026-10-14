"""Convert the approved linked design only. Preserve geometry, bake new prop PBR, reuse legacy materials."""
import bpy,json,re,math,shutil,time
from pathlib import Path
from mathutils import Matrix,Vector
W=Path(__file__).resolve().parent;R=W.parent if W.name=='Scripts' else None
S=R/'ApprovedDesign' if R else W/'source/GunWorkbenchDesign';O=R/'Authored' if R else W/'game_ready';T=O/'Textures';T.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'GunWorkbench_Design_Master.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;dg=bpy.context.evaluated_depsgraph_get();originals=list(scene.objects)
def canon(s):return re.sub(r'\.\d{3}$','',s)
material_cache={};mat_specs={};objects=[];opaque=[];conversion=[];geometry=[]
old_prefix=('WS','GW3','Library_','OriginalLamp')
def local_material(m):
 key=(m.name,m.library.filepath if m.library else '')
 if key in material_cache:return material_cache[key]
 new=m.copy();base=canon(m.name)
 if base.startswith(old_prefix):alias=base
 elif base.startswith('M_ammo_'):alias=base
 elif base.startswith('Smoked safety glazing'):
  bs=new.node_tree.nodes.get('Principled BSDF');alias='GWDesign_OpticGlass' if bs.inputs['Transmission Weight'].default_value<.99 else 'GWDesign_ClearGlass'
 else:alias='PROCEDURAL_'+re.sub(r'\W+','_',base)
 new.name=alias
 material_cache[key]=new
 if alias.startswith('PROCEDURAL_'):
  attr=new.node_tree.nodes.new('ShaderNodeAttribute');attr.attribute_name='ApprovedGenerated'
  for node in new.node_tree.nodes:
   if node.type=='TEX_NOISE' and not node.inputs['Vector'].is_linked:new.node_tree.links.new(attr.outputs['Color'],node.inputs['Vector'])
 mat_specs[new.as_pointer()]=alias
 return new
for src in originals:
 if src.type not in {'MESH','CURVE','FONT'} or src.get('layout_group')=='Studio':continue
 ev=src.evaluated_get(dg);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=dg)
 ob=bpy.data.objects.new('GAME_'+src.name,me);scene.collection.objects.link(ob);ob.matrix_world=src.matrix_world.copy();ob['layout_group']=src.get('layout_group','');ob['approved_source_object']=src.name
 for i,m in enumerate(list(me.materials)):
  if m:me.materials[i]=local_material(m)
 me.calc_loop_triangles();geometry.append({'object':src.name,'source_type':src.type,'group':ob['layout_group'],'triangles':len(me.loop_triangles),'vertices':len(me.vertices)})
 if src.type!='MESH':conversion.append(src.name)
 if any(mat_specs[m.as_pointer()].startswith('PROCEDURAL_') for m in me.materials):
  # Freeze the original per-object Generated coordinates before joining/UV baking.
  lo=[min(v.co[a] for v in me.vertices) for a in range(3)];hi=[max(v.co[a] for v in me.vertices) for a in range(3)]
  at=me.color_attributes.new(name='ApprovedGenerated',type='FLOAT_COLOR',domain='POINT')
  for v,data in zip(me.vertices,at.data):data.color=tuple((v.co[a]-lo[a])/max(hi[a]-lo[a],1e-9) for a in range(3))+(1.,)
  if all(mat_specs[m.as_pointer()].startswith('PROCEDURAL_') for m in me.materials):opaque.append(ob)
 objects.append(ob)
for ob in originals:bpy.data.objects.remove(ob,do_unlink=True)
assert len(objects)==338,len(objects)
bpy.ops.object.select_all(action='DESELECT')
for ob in opaque:ob.select_set(True)
bpy.context.view_layer.objects.active=opaque[0];bpy.ops.object.join();baked=bpy.context.object;baked.name='ApprovedNewProps_PBR'
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for uv in list(baked.data.uv_layers):baked.data.uv_layers.remove(uv)
baked.data.uv_layers.new(name='UVMap');bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.003,area_weight=.5,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.render.threads_mode='FIXED';scene.render.threads=8;scene.render.bake.margin=8;scene.render.bake.use_clear=True
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
mats=list(baked.data.materials);saved={};emission={}
for m in mats:
 if m.as_pointer() in saved:continue
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL')
 saved[m.as_pointer()]=(bs,out)
 emission[m.as_pointer()]=m.node_tree.nodes.new('ShaderNodeEmission')
images={}
for kind in ['Normal','BaseColor','ORM','Emissive']:
 im=bpy.data.images.new('T_GWDesign_Props_'+kind,width=2048,height=2048,alpha=False)
 im.colorspace_settings.name='sRGB' if kind in {'BaseColor','Emissive'} else 'Non-Color'
 for m in mats:
  bs,out=saved[m.as_pointer()];n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=im;m.node_tree.nodes.active=n
  if kind=='Normal':m.node_tree.links.new(bs.outputs[0],out.inputs['Surface'])
  else:
   e=emission[m.as_pointer()]
   if kind=='BaseColor':col=list(bs.inputs['Base Color'].default_value)
   elif kind=='ORM':col=[1,bs.inputs['Roughness'].default_value,bs.inputs['Metallic'].default_value,1]
   else:col=[v*bs.inputs['Emission Strength'].default_value for v in list(bs.inputs['Emission Color'].default_value)[:3]]+[1]
   e.inputs['Color'].default_value=col;e.inputs['Strength'].default_value=1;m.node_tree.links.new(e.outputs[0],out.inputs['Surface'])
 print('BAKE_START',kind,flush=True);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT',normal_space='TANGENT')
 im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();images[kind]=im;print('BAKE_DONE',kind,flush=True)
# Replace all procedural slots by the baked shared PBR material.
bm=bpy.data.materials.new('GWDesign_PropsPBR');bm.use_nodes=True;bs=bm.node_tree.nodes.get('Principled BSDF');nt=bm.node_tree
for kind,im in images.items():
 n=nt.nodes.new('ShaderNodeTexImage');n.image=im
 if kind=='BaseColor':nt.links.new(n.outputs['Color'],bs.inputs['Base Color'])
 elif kind=='Emissive':nt.links.new(n.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1
 elif kind=='ORM':
  sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(n.outputs['Color'],sep.inputs[0]);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 else:
  nm=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(n.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
baked.data.materials.clear();baked.data.materials.append(bm)
for p in baked.data.polygons:p.material_index=0
# Export only the textures used by the table's three approved ammo boxes.
ammo={}
for ob in scene.objects:
 if ob.type!='MESH':continue
 for m in ob.data.materials:
  alias=mat_specs.get(m.as_pointer(),'')
  if not alias.startswith('M_ammo_'):continue
  tex={}
  for n in m.node_tree.nodes:
   if n.type!='TEX_IMAGE' or not n.image:continue
   im=n.image;name=canon(im.name)
   if not name.lower().endswith('.png'):name+='.png'
   target=T/name
   if not target.exists():shutil.copy2(bpy.path.abspath(im.filepath,library=im.library),target)
   tex[name.split('_')[-1].split('.')[0]]=name
  ammo[alias]=tex
# Canonical aliases merge duplicate legacy materials while preserving exact UVs.
canonical={}
for ob in list(scene.objects):
 if ob.type!='MESH':continue
 for i,m in enumerate(ob.data.materials):
  alias=mat_specs.get(m.as_pointer(),m.name)
  if alias not in canonical:canonical[alias]=m;m.name=alias
  ob.data.materials[i]=canonical[alias]
 if not ob.data.uv_layers:ob.data.uv_layers.new(name='UVMap')
 # All exporters should use UV channel zero, with consistent name across joins.
 ob.data.uv_layers[0].name='UVMap';ob.data.uv_layers.active_index=0
for m,alias in [(m,k) for k,m in canonical.items()]:m.name=alias
allob=[o for o in scene.objects if o.type=='MESH'];bpy.ops.object.select_all(action='DESELECT')
for ob in allob:ob.select_set(True)
bpy.context.view_layer.objects.active=baked;bpy.ops.object.join();final=bpy.context.object;final.name='SM_GunWorkbench'
scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
# One slot per actual material. Joining can leave duplicate slots; remap once.
old=list(final.data.materials);unique=[];mapping={}
for i,m in enumerate(old):
 if m not in unique:unique.append(m)
 mapping[i]=unique.index(m)
indices=[mapping[p.material_index] for p in final.data.polygons];final.data.materials.clear()
for m in unique:final.data.materials.append(m)
for p,i in zip(final.data.polygons,indices):p.material_index=i
final.data.calc_loop_triangles();points=[final.matrix_world@v.co for v in final.data.vertices]
assert len(final.data.loop_triangles)==sum(x['triangles'] for x in geometry),(len(final.data.loop_triangles),sum(x['triangles'] for x in geometry))
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'GunWorkbench_GameReady.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SM_GunWorkbench.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
report={'approved_master':str(S/'GunWorkbench_Design_Master.blend'),'fbx':str(O/'SM_GunWorkbench.fbx'),'source_mesh_objects':len(geometry),'converted_curves_and_text':conversion,'triangles':len(final.data.loop_triangles),'vertices':len(final.data.vertices),'bounds_min_m':[min(p[a] for p in points) for a in range(3)],'bounds_max_m':[max(p[a] for p in points) for a in range(3)],'materials':[m.name for m in unique],'ammo_materials':ammo,'baked_textures':{k:v.filepath_raw for k,v in images.items()},'geometry':geometry,'nanite_plan':'disabled for this single mixed opaque/translucent mesh; no shape reduction','approved_source_unchanged':True,'PIE':False}
(O/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('CONVERT_COMPLETE',json.dumps({k:v for k,v in report.items() if k!='geometry'}),flush=True)
