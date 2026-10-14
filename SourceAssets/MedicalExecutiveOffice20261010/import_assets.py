"""Author and save the workstation materials and meshes without opening or running a game."""
import hashlib,json,re,sys,traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/MedicalExecutiveOffice20261010';OWNER='MedicalExecutiveOffice20261010'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active PIE')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report=dict(stage='importing',saved_assets=[],reused_materials=[],tests_run=False,rendered=False,game_run=False)
def record():(ROOT/'Receipts/assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Required dependency unavailable '+path)
 return a
def guard(a):
 if a.get_path_name().split('.')[0] in dirty:raise RuntimeError('Preserve unsaved asset '+a.get_path_name())
def owned(path):
 if not E.does_asset_exist(path):return None
 a=asset(path);guard(a)
 if E.get_metadata_tag(a,'MedicalOffice.Owner')!=OWNER:raise RuntimeError('Preserve unowned asset '+path)
 return a
def save(a):
 E.set_metadata_tag(a,'MedicalOffice.Owner',OWNER)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed '+a.get_path_name())
 report['saved_assets'].append(a.get_path_name());record();return a
def imported(path,source,options=None):
 owned(path)
 task=u.AssetImportTask();task.filename=str(source);task.destination_path,task.destination_name=path.rsplit('/',1)
 task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 if options:task.options=options;task.factory=u.FbxFactory()
 AT.import_asset_tasks([task]);a=asset(path);E.set_metadata_tag(a,'MedicalOffice.Owner',OWNER);return a
def material(key,col=(.028,.035,.043),rough=.48,metal=.15,texture=None,normal=None,roughtex=None,emission=0):
 path=BASE+'/Materials/M_MedOffice_'+key;m=owned(path)
 if m:return m
 m=AT.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
 slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 def scalar(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
 def rgb(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
 def sample(tex,kind):
  n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',asset(tex));n.set_editor_property('sampler_type',kind)
  if key=='Fabric':
   uv=L.create_material_expression(m,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',4);uv.set_editor_property('v_tiling',4);L.connect_material_expressions(uv,'',n,'UVs')
  return n
 def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
 b=sample(texture,u.MaterialSamplerType.SAMPLERTYPE_COLOR) if texture else rgb(col);out='RGB' if texture else ''
 connect(b,out,u.MaterialProperty.MP_BASE_COLOR,'BaseColor')
 connect(sample(roughtex,u.MaterialSamplerType.SAMPLERTYPE_MASKS) if roughtex else scalar(rough),'R' if roughtex else '',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
 connect(scalar(metal),'',u.MaterialProperty.MP_METALLIC,'Metallic');connect(scalar(.28),'',u.MaterialProperty.MP_SPECULAR,'Specular')
 if normal:connect(sample(normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
 if emission:
  mul=L.create_material_expression(m,u.MaterialExpressionMultiply);mul.set_editor_property('const_b',emission)
  L.connect_material_expressions(b,out,mul,'A');connect(mul,'',u.MaterialProperty.MP_EMISSIVE_COLOR,'EmissiveColor')
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 if L.recompile_material(m):raise RuntimeError('Material compilation failed '+key)
 L.layout_material_expressions(m);return save(m)
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
try:
 for source in (ROOT/'Authored/Textures').glob('*.png'):
  t=imported(BASE+'/Textures/'+source.stem,source);t.set_editor_property('srgb',True);t.set_editor_property('never_stream',False)
  t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7);t.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD);save(t)
 material('Graphite')
 rh='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Textures/T_RH2_Fabric_'
 material('Fabric',col=(.022,.030,.034),rough=.86,metal=0,normal=rh+'NormalDX',roughtex=rh+'Roughness')
 material('Print',rough=.78,metal=0,texture=BASE+'/Textures/T_MedicalOffice_Print')
 material('Screen',rough=.33,metal=0,texture=BASE+'/Textures/T_MedicalOffice_Screen',emission=.25)
 for item in json.loads((ROOT/'Config/geometry.json').read_text('utf8'))['meshes']:
  path=item['mesh'];options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
  options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
  data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.one_convex_hull_per_ucx=True
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
  try:
   u.SystemLibrary.execute_console_command(None,flag+' 0');mesh=imported(path,item['fbx'],options)
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mp=item['materials'][key];mat=asset(mp)
   ensure_material_usage(mat,guard);mesh.set_material(i,mat)
   if not mp.startswith(BASE) and mp not in report['reused_materials']:report['reused_materials'].append(mp)
  mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  build=SM.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True;build.recompute_tangents=True;SM.set_lod_build_settings(mesh,0,build)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True;ns.generate_fallback=u.NaniteGenerateFallback.ENABLED
  ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;ns.fallback_percent_triangles=1.;ns.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',ns)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
  E.set_metadata_tag(mesh,'MedicalOffice.SourceSHA256',hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest());save(mesh)
  print('MEDICAL_EXECUTIVE_ASSET_SAVED',path,flush=True)
 report['stage']='assets_saved';record();print('MEDICAL_EXECUTIVE_ASSETS_SAVED',flush=True)
except Exception:
 report.update(stage='incomplete',error=traceback.format_exc());record();raise
