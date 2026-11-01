"""Import the two differentiated seats into isolated V9 packages and save them."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/SeatDistinctV9'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
manifest=json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))
A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt=dict(complete=False,models=[],materials=[],textures=[],saved=[],runtime_tested=False)
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
 asset.modify()
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
 receipt['saved'].append(asset.get_path_name());record()
def imp(file,name,folder,options=None):
 asset=u.load_asset(folder+'/'+name)
 if asset:return asset
 task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder;task.automated=True;task.save=False
 if options:task.options=options
 A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
 if not asset:raise RuntimeError('Import failed '+name)
 return asset
record()
for part in ('Crown','ReturnRing'):
 textures={}
 for kind in ('BaseColor','ORM','Normal'):
  name='T_ThunderSeatV9_'+part+'_'+kind;file=P/'Textures'/(name+'.png');tex=imp(file,name,D+'/Textures');normal=kind=='Normal'
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
  tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('flip_green_channel',normal)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON)
  tex.set_editor_property('max_texture_size',2048);tex.set_editor_property('never_stream',False)
  save(tex);textures[kind]=tex;receipt['textures'].append(tex.get_path_name())
 name='M_ThunderSeatV9_'+part;mat=u.load_asset(D+'/'+name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
 L.delete_all_material_expressions(mat);mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('two_sided',False)
 surface=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 nodes={}
 for kind,tex in textures.items():
  node=L.create_material_expression(mat,u.MaterialExpressionTextureSample);node.set_editor_property('texture',tex)
  node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[kind]=node
 for key,ch,pin,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),('ORM','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),('ORM','B','Metallic',u.MaterialProperty.MP_METALLIC),('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
  if not L.connect_material_expressions(nodes[key],ch,surface,pin):raise RuntimeError('Material input '+pin)
  L.connect_material_property(nodes[key],ch,prop)
 L.connect_material_property(nodes['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
 if not L.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output missing')
 L.layout_material_expressions(mat);L.recompile_material(mat);save(mat);receipt['materials'].append(mat.get_path_name())
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
for row in manifest['parts']:
 mesh=imp(P/'Export'/(row['mesh']+'.fbx'),row['mesh'],D+'/Meshes',opt)
 bindings={entry['slot']:u.load_asset(entry['asset']) for entry in row['materials']}
 for i,slot in enumerate(mesh.get_editor_property('static_materials')):
  material=bindings.get(str(slot.material_slot_name))
  if not material:raise RuntimeError('Missing material binding '+str(slot.material_slot_name))
  mesh.set_material(i,material)
 settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;settings.explicit_tangents=True;settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
 subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);build=subsystem.get_lod_build_settings(mesh,0)
 build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_normals',False);build.set_editor_property('recompute_tangents',True);build.set_editor_property('use_mikk_t_space',True);subsystem.set_lod_build_settings(mesh,0,build)
 u.EditorAssetLibrary.set_metadata_tag(mesh,'AuthoringRevision','SeatDistinctV9');save(mesh)
 receipt['models'].append(dict(id=row['id'],mesh=mesh.get_path_name(),materials=[m.get_path_name() for m in bindings.values()],fbx_sha256=hashlib.sha256((P/'Export'/(row['mesh']+'.fbx')).read_bytes()).hexdigest()))
receipt['complete']=True;record();print('THUNDER_DISTINCT_V9_ASSETS_SAVED')
