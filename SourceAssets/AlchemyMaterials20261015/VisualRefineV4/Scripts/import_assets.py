"""Save new alchemy meshes, PBR atlas and thin-translucent glass in a content-only host."""
from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
DEST='/Game/Items/AlchemyMaterials20261015/V4';OWNER='AlchemyMaterials20261015'
SPEC=json.loads((ROOT/'model_manifest.json').read_text('utf8'))
HOST=Path(u.Paths.project_dir()).resolve();STAGED=HOST==(ROOT/'UEImportHost').resolve()
if not STAGED and HOST!=PROJECT.resolve():raise RuntimeError('Wrong project')
if not STAGED and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 level=u.get_editor_subsystem(u.LevelEditorSubsystem)
 if level and level.is_in_play_in_editor():raise RuntimeError('Preserve active PIE before replacing loaded meshes')
 for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
  if package.get_name().startswith('/Game/Items/AlchemyMaterials20261015/'):
   raise RuntimeError('Preserve unsaved task asset '+package.get_name())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report=dict(stage='importing',host=str(HOST),meshes=[],materials=[],textures=[],material_compile_errors=[],runtime_tested=False)
def record():(ROOT/'Receipts/ue-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
def save(o):
 E.set_metadata_tag(o,'Alchemy.Owner',OWNER)
 if not E.save_loaded_asset(o,False):raise RuntimeError('Save failed '+o.get_path_name())
def imp(source,name,folder,options=None):
 path=folder+'/'+name
 if E.does_asset_exist(path):
  obj=u.load_asset(path)
  if E.get_metadata_tag(obj,'Alchemy.Owner')!=OWNER:raise RuntimeError('Preserve unowned asset '+path)
  if not options:return obj
 t=u.AssetImportTask();t.filename=str(source);t.destination_name=name;t.destination_path=folder;t.automated=True;t.save=False;t.replace_existing=options is not None;t.replace_existing_settings=options is not None
 if options:t.options=options;t.factory=u.FbxFactory()
 else:t.factory=u.TextureFactory()
 A.import_asset_tasks([t]);obj=u.load_asset(path)
 if not obj:raise RuntimeError('Import failed '+path)
 E.set_metadata_tag(obj,'Alchemy.Owner',OWNER);return obj
def connect(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Connection failed '+pin)
def prop(a,socket,kind):
 if not L.connect_material_property(a,socket,kind):raise RuntimeError('Output failed '+str(kind))
def scalar(mat,value,kind):
 n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.r=value;prop(n,'',kind);return n
def color(mat,value):
 n=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.constant=u.LinearColor(*value,1);return n
def newmat(name):
 path=DEST+'/Materials/'+name
 m=u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
 if E.does_asset_exist(path) and E.get_metadata_tag(m,'Alchemy.Owner') not in ('',OWNER):raise RuntimeError('Preserve unowned material')
 for node in list(L.get_material_expressions(m)):L.delete_material_expression(m,node)
 return m
def finish(m):
 errors=L.recompile_material(m)
 if errors:
  report['material_compile_errors'].append({'material':m.get_name(),'errors':[str(e) for e in errors]});record();raise RuntimeError(str(errors))
 L.layout_material_expressions(m);save(m);report['materials'].append(m.get_path_name())
record();textures={}
spec=next(iter(SPEC['assets'].values()))
for kind,source in spec['textures'].items():
 tex=imp(source,'T_Alchemy_'+kind,DEST+'/Textures');tex.set_editor_property('srgb',kind=='BaseColor')
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS if kind=='ORM' else u.TextureCompressionSettings.TC_BC7)
 tex.set_editor_property('max_texture_size',4096)
 if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
 save(tex);textures[kind]=tex;report['textures'].append(tex.get_path_name())
mat=newmat('M_Alchemy_Surface');mat.set_editor_property('used_with_instanced_static_meshes',True)
slab=L.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
nodes={}
for kind,tex in textures.items():
 n=L.create_material_expression(mat,u.MaterialExpressionTextureSample);n.texture=tex
 n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR);nodes[kind]=n
for n,socket,pin,kind in [(nodes['BaseColor'],'RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),(nodes['ORM'],'G','Roughness',u.MaterialProperty.MP_ROUGHNESS),(nodes['ORM'],'B','Metallic',u.MaterialProperty.MP_METALLIC),(nodes['Normal'],'RGB','Normal',u.MaterialProperty.MP_NORMAL)]:
 connect(n,socket,slab,pin);prop(n,socket,kind)
prop(nodes['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION);prop(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);finish(mat)
mats={'M_Alchemy_Surface':mat}
for key,(base,rough,tint) in SPEC['glass_materials'].items():
 name='M_Alchemy_'+key;m=newmat(name)
 prop(color(m,base),'',u.MaterialProperty.MP_BASE_COLOR);scalar(m,rough,u.MaterialProperty.MP_ROUGHNESS);scalar(m,0,u.MaterialProperty.MP_METALLIC)
 m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_THIN_TRANSLUCENT)
 m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING);m.set_editor_property('two_sided',False)
 thin=L.create_material_expression(m,u.MaterialExpressionThinTranslucentMaterialOutput)
 connect(color(m,tint),'',thin,str(L.get_material_expression_input_names(thin)[0]));scalar(m,0,u.MaterialProperty.MP_OPACITY)
 finish(m);mats[name]=m
u.load_module('StaticMeshEditor');SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if not SM:SM=u.new_object(u.StaticMeshEditorSubsystem)
for key,spec in SPEC['assets'].items():
 options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False
 options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 d=options.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
 d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False
 d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 mesh=imp(spec['fbx'],spec['mesh'],'/Game/Items/AlchemyMaterials20261015/V3/Meshes',options)
 for i,slot in enumerate(mesh.static_materials):
  name=str(slot.material_slot_name)
  if name not in mats:raise RuntimeError('Unbound material slot '+name)
  mesh.set_material(i,mats[name])
 settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_tangents=True;settings.recompute_normals=False;settings.use_mikk_t_space=True
 SM.set_lod_build_settings(mesh,0,settings)
 nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;SM.set_nanite_settings(mesh,nanite,True)
 save(mesh);report['meshes'].append(dict(item_id=spec['id'],path=mesh.get_path_name(),triangles_lod0=spec['triangles_lod0'],collision_hulls=spec['collision_hulls'],nanite_enabled=False,glass='Thin Translucent; separate glass/liquid slots'))
 record();u.log('ALCHEMY_ASSET_SAVED '+mesh.get_path_name())
report['stage']='staged_assets_saved' if STAGED else 'assets_saved';record();u.log('ALCHEMY_IMPORT_COMPLETE')
