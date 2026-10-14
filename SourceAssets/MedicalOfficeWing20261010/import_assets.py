"""Import/save authored shell, reuse existing materials and read the latest catalog."""
import json,re,runpy,sys,traceback
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
report=read(ROOT/'Receipts/assets.json') if (ROOT/'Receipts/assets.json').exists() else dict(saved_assets=[])
report.update(stage='importing',tested=False,game_run=False,rendered=False);report.pop('error',None)
def record():(ROOT/'Receipts/assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();SM=(u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem))
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def guard(asset):
 if asset.get_path_name().split('.')[0] in dirty:raise RuntimeError('Preserve unsaved asset '+asset.get_path_name())
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_material_usage
try:
 for item in read(ROOT/'Config/geometry.json')['meshes']:
  if globals().get('IMPORT_KINDS') and item['kind'] not in IMPORT_KINDS:continue
  path=item['mesh']
  if path in dirty:raise RuntimeError('Preserve unsaved office mesh '+path)
  task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=item['name']
  task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
  options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
  options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
  data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.one_convex_hull_per_ucx=True
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  task.options=options;task.factory=u.FbxFactory()
  flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
  try:
   u.SystemLibrary.execute_console_command(None,flag+' 0');AT.import_asset_tasks([task])
  finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
  mesh=u.load_asset(path)
  if not mesh:raise RuntimeError('Office mesh import failed '+path)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
   if not material:raise RuntimeError('Reused material unavailable '+item['materials'][key])
   ensure_material_usage(material,guard);mesh.set_material(i,material)
  mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
  build=SM.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True);SM.set_lod_build_settings(mesh,0,build)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True
  ns.generate_fallback=u.NaniteGenerateFallback.ENABLED;ns.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
  ns.fallback_percent_triangles=1.;ns.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',ns)
  if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Office Nanite build failed '+path)
  if not E.save_loaded_asset(mesh,False):raise RuntimeError('Office mesh save failed '+path)
  
  if path not in report['saved_assets']:report['saved_assets'].append(path)
  record();print('MEDICAL_OFFICE_ASSET_SAVED',path,flush=True)
 if globals().get('GEOMETRY_ONLY'):
  report.update(stage='assets_saved');record();print('MEDICAL_OFFICE_FINISHES_SAVED',flush=True)
 else:
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
  editor=(u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem))
  if editor.get_game_world():raise RuntimeError('Preserve active PIE')
  prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
  world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
  gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
  text=gen.get_editor_property('module_catalog_json');(ROOT/'Config/catalog-input.json').write_text(text,encoding='utf8')
  catalog=runpy.run_path(str(ROOT/'recipe.py'))['apply'](json.loads(text))
  (ROOT/'Config/catalog-pending.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')),encoding='utf8')
  if prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
  report.update(stage='assets_saved',catalog_prepared=True);record()
except Exception:
 report.update(stage='import_incomplete',error=traceback.format_exc());record();raise
