"""Import ward geometry for the independent subject. No pool mutation."""
import hashlib,json,re,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text(encoding='utf-8'))
MAN=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
MAN['objects']+=json.loads((ROOT/'Authored/door-manifest.json').read_text(encoding='utf-8'))['objects']
MAN['objects']+=json.loads((ROOT/'Authored/breakable-glass-manifest.json').read_text(encoding='utf-8'))['objects']
if globals().get('WARD_IMPORT_NAMES'):
 MAN['objects']=[item for item in MAN['objects'] if item['name'] in WARD_IMPORT_NAMES]

BASE=CFG['ue_base'];IMPORT_REVISION='ward_glass_ucx_atmosphere_v2'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE and UE.get_game_world():raise RuntimeError('Preserve active PIE')
initial_dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
receipt_path=ROOT/'Receipts/install.json'
report=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {'meshes':{},'saved_assets':[]}
def record():receipt_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def guard(asset):
 if asset.get_path_name().split('.')[0] in initial_dirty:raise RuntimeError('Preserve unsaved asset '+asset.get_path_name())
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
 record()
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage

meshes={}
for item in MAN['objects']:
 path=BASE+'/Meshes/'+item['name'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
 if path in initial_dirty:raise RuntimeError('Preserve unsaved ward mesh '+path)
 old=report['meshes'].get(item['name'])
 mesh=u.load_asset(path) if E.does_asset_exist(path) else None
 if mesh and old and old.get('source_sha256')==digest and old.get('import_revision')==IMPORT_REVISION:
  meshes[item['kind']]=mesh;continue
 task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
 task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
 options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
 options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
 data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
 data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
 data.one_convex_hull_per_ucx=True
 data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
 data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
 task.options=options;task.factory=u.FbxFactory()
 # Interchange reimport retains the old no-collision body for these existing panes.
 # Use the FBX UCX importer for authored collision, scoped to this one import call.
 flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
 try:
  if item.get('collision_boxes'):u.SystemLibrary.execute_console_command(None,flag+' 0')
  AT.import_asset_tasks([task])
 finally:
  if item.get('collision_boxes'):u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Ward mesh import failed '+path)
 mesh.modify()
 for index,slot in enumerate(mesh.get_editor_property('static_materials')):
  key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
  if not material:raise RuntimeError('Missing reused material '+item['materials'][key])
  ensure_material_usage(material,guard);mesh.set_material(index,material)
 mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
   u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item.get('collision_boxes') else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
 settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True
 settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
 settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0
 mesh.set_editor_property('nanite_settings',settings)
 if item.get('full_precision_uvs'):
  editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
  build=editor.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
  editor.set_lod_build_settings(mesh,0,build)
 if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Ward Nanite build failed '+path)
 if item.get('collision_boxes'):
  aggregate=mesh.get_editor_property('body_setup').get_editor_property('agg_geom')
  shapes=sum(len(aggregate.get_editor_property(k)) for k in ('box_elems','sphere_elems','sphyl_elems','convex_elems'))
  if shapes<item['collision_boxes']:raise RuntimeError('Glass UCX volumes not imported '+path)
 save(mesh);meshes[item['kind']]=mesh
 report['meshes'][item['name']]={'path':path,'source_sha256':digest,'source_triangles':item['triangles'],'collision':item['collision'],'collision_boxes':item.get('collision_boxes',0),'nanite':item['nanite'],'import_revision':IMPORT_REVISION}
 record();print('WARD_MESH_SAVED',item['kind'],flush=True)

report.update(stage='meshes_saved',revision=CFG['revision'],tests_run=False,rendered=False)
record()
print('WARD_POOL_MESHES_SAVED',len(meshes),flush=True)
