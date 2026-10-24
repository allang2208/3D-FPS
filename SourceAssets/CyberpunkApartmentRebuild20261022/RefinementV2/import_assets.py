"""Import and save only this revision's new meshes and finishes, in the background."""
import json,hashlib,sys,re,traceback
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from refinement_design import *
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
OWNER='CyberpunkApartment.RefinementV2'
BASIS_POLICY='authored_normals_segmented_edges_mikk_v2'
manifest=json.loads((ROOT/'assembly.json').read_text('utf8'))
receipt=ROOT/'assets_saved.json'
report=json.loads(receipt.read_text('utf8')) if receipt.exists() else dict(meshes={},materials={},stage='preparing')
report.update(tests_run=False,game_run=False,rendered=False)
def record():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
def asset(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Required authoring dependency is missing: '+path)
 return a
def save(a):
 a.modify();E.set_metadata_tag(a,'Apartment.Owner',OWNER)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def finish(key):
 path=MATERIALS[key];m=u.load_asset(path) if E.does_asset_exist(path) else None
 if m and E.get_metadata_tag(m,'Apartment.Owner')!=OWNER:raise RuntimeError('Preserve unowned asset '+path)
 if m and report['materials'].get(key):return m
 if not m:m=AT.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
 m.modify();L.delete_all_material_expressions(m)
 m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
 slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
 slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
 def constant(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
 def rgb(v):
  n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
 def wire(n,pin,prop):
  L.connect_material_expressions(n,'',slab,pin);L.connect_material_property(n,'',prop)
 color,rough,metal,emission=FINISHES[key]
 if key=='SmokedWood':
  base=L.create_material_expression(m,u.MaterialExpressionTextureSample)
  base.set_editor_property('texture',asset('/Game/SubstrateMaterials/Textures/08_WoodVeneer/T_WoodVeneer_Oak_BC'))
  base.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  tint=L.create_material_expression(m,u.MaterialExpressionMultiply)
  L.connect_material_expressions(base,'R',tint,'A');L.connect_material_expressions(rgb(color),'',tint,'B')
  wire(tint,'BaseColor',u.MaterialProperty.MP_BASE_COLOR)
  normal=L.create_material_expression(m,u.MaterialExpressionTextureSample)
  normal.set_editor_property('texture',asset('/Game/SubstrateMaterials/Textures/08_WoodVeneer/T_WoodVeneer_Oak_N'))
  normal.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
  L.connect_material_expressions(normal,'RGB',slab,'Normal');L.connect_material_property(normal,'RGB',u.MaterialProperty.MP_NORMAL)
 else:wire(rgb(color),'BaseColor',u.MaterialProperty.MP_BASE_COLOR)
 wire(constant(rough),'Roughness',u.MaterialProperty.MP_ROUGHNESS)
 wire(constant(metal),'Metallic',u.MaterialProperty.MP_METALLIC)
 wire(constant(.35),'Specular',u.MaterialProperty.MP_SPECULAR)
 if emission:wire(rgb([v*emission for v in color]),'EmissiveColor',u.MaterialProperty.MP_EMISSIVE_COLOR)
 L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile failed '+key+': '+str(errors))
 save(m);report['materials'][key]=path;record();return m

try:
 if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
 for key in FINISHES:finish(key)
 # FBX importer respects authored UCX; no automatic room-sized convex collision.
 u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 for row in manifest['meshes']:
  digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
  previous=report['meshes'].get(row['key'],{})
  mesh=u.load_asset(row['asset']) if E.does_asset_exist(row['asset']) else None
  if mesh and previous.get('source_sha256')==digest and previous.get('basis_policy')==BASIS_POLICY:continue
  if mesh and E.get_metadata_tag(mesh,'Apartment.Owner')!=OWNER:raise RuntimeError('Preserve unowned mesh '+row['asset'])
  task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=row['name']
  task.automated=True;task.replace_existing=True;task.save=False
  options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
  options.import_as_skeletal=False;options.automated_import_should_detect_type=False
  options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  data=options.static_mesh_import_data
  data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
  data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
  data.one_convex_hull_per_ucx=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
  task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=asset(row['asset'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):
   key=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name))
   mesh.set_material(i,asset(row['materials'][key]))
  body=mesh.get_editor_property('body_setup')
  body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  build=SM.get_lod_build_settings(mesh,0)
  build.set_editor_property('use_full_precision_u_vs',True)
  build.set_editor_property('use_high_precision_tangent_basis',True)
  # Source bevels are segmented before triangulation, avoiding acute slivers.
  # Preserve the authored normals and use the standard Mikk basis for shared PBR.
  build.set_editor_property('use_mikk_t_space',True)
  build.set_editor_property('recompute_tangents',True)
  build.set_editor_property('recompute_normals',False)
  SM.set_lod_build_settings(mesh,0,build)
  settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=row['nanite'];settings.explicit_tangents=True
  settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
  settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
  settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.
  mesh.set_editor_property('nanite_settings',settings)
  if row['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+row['name'])
  if not row['nanite'] and row['triangles']>18000 and not row['key'].startswith('Door_'):
   opt=u.StaticMeshReductionOptions();opt.auto_compute_lod_screen_size=False
   opt.reduction_settings=[u.StaticMeshReductionSettings(percent_triangles=p,screen_size=s)
                          for p,s in ((1.,1.),(.65,.12),(.35,.035))]
   SM.set_lods(mesh,opt)
  save(mesh)
  report['meshes'][row['key']]=dict(path=row['asset'],source_sha256=digest,
    triangles=row['triangles'],nanite=row['nanite'],collision_hulls=row['hulls'],saved=True,basis_policy=BASIS_POLICY)
  report['stage']='importing';record()
 report['shared_assets']={key:asset(path).get_path_name() for key,path in REUSE.items()}
 report['stage']='assets_saved';record();u.log('APARTMENT_REBUILD_ASSETS_SAVED '+str(len(report['meshes'])))
except Exception:
 report['stage']='failed';report['error']=traceback.format_exc();record();raise
