import unreal as u,json,re,hashlib,os,builtins,math
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/gunbench_import_20261006');P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/GunWorkbenchApproved20261006/Authored'
DEST='/Game/Building/GunWorkbenchApproved20261006';TARGET='/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench'
assert '-GunWorkbenchApproved20261006' in u.SystemLibrary.get_command_line()
assert Path(u.Paths.project_dir()).resolve()==P.resolve()
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);assert not ed.get_game_world()
assert os.getpid()==json.loads((W/'editor_owner.json').read_text(encoding='utf-8-sig'))['pid']
before=json.loads((W/'ue_before.json').read_text());man=json.loads((S/'manifest.json').read_text())
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Dirty content before import'
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Dirty map before import'
for rec in json.loads((W/'backup_receipt.json').read_text()):
 if rec['path'].endswith('.uasset'):assert hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()==rec['sha256'],('Concurrent asset change',rec['path'])
def canon(s):return re.sub(r'[._]\d{3}$','',str(s))
def normalized(s):return re.sub(r'0x[0-9A-Fa-f]+','POINTER',str(s))
pal=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette');entries=list(pal.components)
assert [normalized(e) for e in entries]==[normalized(e) for e in before['palette_entries']],'Palette changed since snapshot'
ei=next(i for i,e in enumerate(entries) if str(e.id)=='gun_workbench_table');entry=entries[ei]
mesh=u.load_asset(TARGET);assert entry.mesh==mesh
materials={canon(m['slot']):u.load_asset(m['path']) for m in before['materials']}
textures={};created=[]
def save(obj):
 assert E.save_loaded_asset(obj,False),('Save failed',obj.get_path_name())
 if obj.get_path_name() not in created:created.append(obj.get_path_name())
def node(m,kind):return L.create_material_expression(m,kind)
def prop(n,out,p):assert L.connect_material_property(n,out,p),(n,p)
def link(n,out,to,p):assert L.connect_material_expressions(n,out,to,p),(out,p)
def scalar(m,v,p):n=node(m,u.MaterialExpressionConstant);n.r=v;prop(n,'',p);return n
def color(m,v):n=node(m,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*v[:3],1);return n
tasks=[]
for p in sorted((S/'Textures').glob('*.png')):
 assert not E.does_asset_exist(DEST+'/Textures/'+p.stem),'Import destination already exists'
 t=u.AssetImportTask();t.filename=str(p);t.destination_path=DEST+'/Textures';t.destination_name=p.stem;t.automated=True;t.save=False;t.replace_existing=False;tasks.append(t)
A.import_asset_tasks(tasks)
for p in sorted((S/'Textures').glob('*.png')):
 t=u.load_asset(DEST+'/Textures/'+p.stem);assert isinstance(t,u.Texture2D),p.name
 kind=p.stem.rsplit('_',1)[-1];t.set_editor_property('srgb',kind in ['BaseColor','Emissive'])
 if kind=='Normal':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);t.set_editor_property('flip_green_channel',True)
 elif kind=='ORM':t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
 t.set_editor_property('never_stream',False);save(t);textures[p.name]=t
def newmat(name):
 assert not E.does_asset_exist(DEST+'/Materials/'+name),name
 return A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
def pbr(name,maps):
 m=newmat(name)
 for kind,filename in maps.items():
  n=node(m,u.MaterialExpressionTextureSample);n.texture=textures[filename]
  if kind=='Normal':n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL;prop(n,'RGB',u.MaterialProperty.MP_NORMAL)
  elif kind=='ORM':
   n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
   for ch,p in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:prop(n,ch,p)
  else:prop(n,'RGB',u.MaterialProperty.MP_BASE_COLOR if kind=='BaseColor' else u.MaterialProperty.MP_EMISSIVE_COLOR)
 errors=L.recompile_material(m);assert not errors,errors;save(m);return m
materials['GWDesign_PropsPBR']=pbr('M_GWDesign_PropsPBR',{k:Path(v).name for k,v in man['baked_textures'].items()})
sharedmetal=None
for alias,maps in man['ammo_materials'].items():
 if alias.endswith('_Metal'):
  if sharedmetal is None:sharedmetal=pbr('M_GWDesign_AmmoMetal',maps)
  materials[alias]=sharedmetal
 else:materials[alias]=pbr(alias.replace('M_ammo_','M_GWDesign_Ammo_'),maps)
for alias,tint,rough in [('GWDesign_ClearGlass',[.90,.96,.97],.022),('GWDesign_OpticGlass',[.43,.66,.71],.07)]:
 m=newmat('M_'+alias);m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT);m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);m.set_editor_property('two_sided',False)
 c=color(m,tint);prop(c,'',u.MaterialProperty.MP_BASE_COLOR);scalar(m,rough,u.MaterialProperty.MP_ROUGHNESS);scalar(m,0,u.MaterialProperty.MP_METALLIC);scalar(m,0,u.MaterialProperty.MP_OPACITY)
 thin=node(m,u.MaterialExpressionThinTranslucentMaterialOutput);link(c,'',thin,str(L.get_material_expression_input_names(thin)[0]));errors=L.recompile_material(m);assert not errors,errors;save(m);materials[alias]=m
assert all(alias in materials and materials[alias] for alias in man['materials']),set(man['materials'])-set(materials)
for cal in ['556','762']:
 materials['Ammo_ammo_'+cal+'_0']=materials['M_ammo_'+cal+'_Paper'];materials['Ammo_ammo_'+cal+'_1']=materials['M_ammo_'+cal+'_Metal']
task=u.AssetImportTask();task.filename=str(S/'SM_GunWorkbench.fbx');task.destination_path=TARGET.rsplit('/',1)[0];task.destination_name='SM_GunWorkbench';task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=u.load_asset(TARGET);assert mesh
slots=list(mesh.static_materials)
assert canon(slots[0].material_slot_name)=='WSBench_BenchWood',('Unsafe slot zero',slots[0].material_slot_name)
for i,slot in enumerate(slots):
 key=canon(slot.material_slot_name);assert key in materials,key;mesh.set_material(i,materials[key])
nan=mesh.get_editor_property('nanite_settings');nan.enabled=False;mesh.set_editor_property('nanite_settings',nan)
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
build=sub.get_lod_build_settings(mesh,0)
for k,v in {'remove_degenerates':False,'recompute_normals':False,'recompute_tangents':False,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True,'generate_lightmap_u_vs':False}.items():build.set_editor_property(k,v)
sub.set_lod_build_settings(mesh,0,build);nan.fallback_relative_error=0.;nan.fallback_percent_triangles=1.;sub.set_nanite_settings(mesh,nan,True);sub.remove_collisions(mesh)
body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
E.set_metadata_tag(mesh,'ApprovedGunWorkbenchSourceSHA256',hashlib.sha256((S/'SM_GunWorkbench.fbx').read_bytes()).hexdigest())
E.set_metadata_tag(mesh,'ApprovedGunWorkbenchDesign','20261006 approved linked Blender V2; static import only')
save(mesh)
b=mesh.get_bounds();bo=before['bounds_origin'];delta=[b.origin.x-bo[0],b.origin.y-bo[1],b.origin.z-bo[2]]
assert abs(delta[0])<.001 and abs(delta[1])<.001,('Horizontal bounds changed; cannot compensate all yaw orientations with one static offset',delta)
assert 6.5<delta[2]<6.7,delta
old=before['pivot_offset_cm'];entry.set_editor_property('pivot_offset_cm',u.Vector(old[0],old[1],old[2]+delta[2]));entries[ei]=entry;pal.set_editor_property('components',entries)
assert all(normalized(e)==normalized(before['palette_entries'][i]) for i,e in enumerate(pal.components) if i!=ei),'Unrelated palette entries changed'
save(pal)
report={'saved':True,'mesh':mesh.get_path_name(),'materials':[{'slot':str(x.material_slot_name),'path':x.material_interface.get_path_name()} for x in mesh.static_materials],'bounds_origin_cm':[b.origin.x,b.origin.y,b.origin.z],'bounds_extent_cm':[b.box_extent.x,b.box_extent.y,b.box_extent.z],'bounds_center_delta_cm':delta,'pivot_offset_before_cm':old,'pivot_offset_after_cm':[entry.pivot_offset_cm.x,entry.pivot_offset_cm.y,entry.pivot_offset_cm.z],'footprint':[entry.footprint.x,entry.footprint.y,entry.footprint.z],'collision':str(body.get_editor_property('collision_trace_flag')),'nanite_enabled':bool(mesh.get_editor_property('nanite_settings').enabled),'created_or_saved':created,'source_triangles':man['triangles'],'PIE':False,'cpp_modified':False,'maps_saved':False}
(W/'ue_import_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8');(P/'SourceAssets/GunWorkbenchApproved20261006/import_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
builtins.gunbench_state.update(mesh=mesh,palette=pal,import_receipt=report)
print('GUNBENCH_IMPORTED '+json.dumps({k:v for k,v in report.items() if k not in ['materials','created_or_saved']}))
