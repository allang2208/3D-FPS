"""Import the GuanLei C7 seat into new isolated packages; no gameplay changes."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/GuanLeiReturnC8'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
assert manifest['complete'] and len(manifest['parts'])==1
assert json.loads((P/'texture_manifest.json').read_text(encoding='utf-8'))['complete']
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'complete':False,'models':[],'textures':[],'saved':[],'runtime_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
 receipt['saved'].append(asset.get_path_name());record()
def imp(file,name,folder,options=None):
 asset=u.load_asset(folder+'/'+name)
 if asset and options:return asset
 t=u.AssetImportTask();t.filename=str(file);t.destination_name=name;t.destination_path=folder;t.automated=True;t.save=False;t.replace_existing=False
 if asset:t.replace_existing=True;t.replace_existing_settings=True
 if options:t.options=options
 A.import_asset_tasks([t]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 return asset
record()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
for row in manifest['parts']:
 textures={}
 for kind,rel in row['textures'].items():
  file=P/rel;name=file.stem;tex=imp(file,name,D+'/Textures');normal=kind=='Normal'
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
  tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('flip_green_channel',normal)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON)
  tex.set_editor_property('max_texture_size',4096);tex.set_editor_property('never_stream',False);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
  save(tex);textures[kind]=tex
  receipt['textures'].append({'id':row['id'],'kind':kind,'asset':tex.get_path_name(),'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'compression':str(tex.get_editor_property('compression_settings')),'srgb':tex.get_editor_property('srgb'),'flip_green_channel':tex.get_editor_property('flip_green_channel'),'lod_group':str(tex.get_editor_property('lod_group'))});record()
 name='M_GuanLeiC8_'+row['id'];mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat);mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('two_sided',True)
 surface=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 nodes={}
 for kind,tex in textures.items():
  n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[kind]=n
 for key,ch,pin,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('ORM','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),('ORM','B','Metallic',u.MaterialProperty.MP_METALLIC),('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
  if not L.connect_material_expressions(nodes[key],ch,surface,pin):raise RuntimeError('Material input '+pin)
  L.connect_material_property(nodes[key],ch,prop)
 if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output missing')
 L.layout_material_expressions(mat);errors=L.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 save(mat)
 mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D+'/Meshes',opt)
 for i,s in enumerate(mesh.get_editor_property('static_materials')):
  key=str(s.material_slot_name)
  if key==name:mesh.set_material(i,mat)
  else:raise RuntimeError('Unexpected material slot '+key)
 settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True;settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
 subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);build=subsystem.get_lod_build_settings(mesh,0)
 build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_mikk_t_space',True)
 subsystem.set_lod_build_settings(mesh,0,build)
 box=mesh.get_bounding_box();size=box.max-box.min;got=[size.x,size.y,size.z];expected=[(row['bounds_m'][1][i]-row['bounds_m'][0][i])*100 for i in range(3)]
 if any(abs(a-b)>.05 for a,b in zip(got,expected)):raise RuntimeError('Import scale mismatch '+row['id'])
 save(mesh)
 receipt['models'].append({'id':row['id'],'mesh':mesh.get_path_name(),'size_cm':got,'material_paths':[s.material_interface.get_path_name() for s in mesh.get_editor_property('static_materials')],'normal_asset':textures['Normal'].get_path_name(),'appearance':row['appearance'],'fbx_sha256':hashlib.sha256((P/'Export'/(row['mesh']+'.fbx')).read_bytes()).hexdigest()});record()
receipt['complete']=True;record();print('GUANLEI_C8_ASSETS_SAVED')
