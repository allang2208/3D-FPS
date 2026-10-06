"""Import and save all nine fitted stock assets; no runtime tests."""
import json,re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/LegendaryStock20261006/Integration'
auth=json.loads((O/'fitted-models.json').read_text());D='/Game/Weapons/LegendaryStock20261006'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
report={'saved':[],'models':{},'game_tested':False,'status':'importing'}
report['visual_revision']=auth.get('visual_revision','V1')
targets={v['asset'] for v in auth['models'].values()}
if targets.intersection({p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}):
 raise RuntimeError('Preserve unsaved tactical-stock fitting edits')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Finish current PIE before fitting import')
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
 for family,entry in auth['models'].items():
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_name=entry['name'];task.destination_path=D+'/Fitted'
  task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt;task.factory=u.FbxFactory();task.save=False
  A.import_asset_tasks([task]);mesh=u.load_asset(entry['asset'])
  if mesh is None or not task.imported_object_paths:raise RuntimeError('Fitting import failed: '+family)
  slots=list(mesh.static_materials)
  for i,s in enumerate(slots):
   key=re.sub(r'[._]\d{3}$','',str(s.material_slot_name));mat=u.load_asset(D+'/Materials/M_'+key)
   if mat is None:raise RuntimeError('Missing stock material '+key)
   s.material_interface=mat;slots[i]=s
  mesh.set_editor_property('static_materials',slots)
  E.set_metadata_tag(mesh,'DisplayName','可调式战术后托');E.set_metadata_tag(mesh,'PartId','legendary_adjustable_tactical_stock')
  E.set_metadata_tag(mesh,'WeaponFamily',family);E.set_metadata_tag(mesh,'Frame','WPN_root physical centimetres; relative scale 0.01')
  E.set_metadata_tag(mesh,'Source',str(O/'Editable'/(family+'_TacticalStock.blend')))
  E.set_metadata_tag(mesh,'VisualRevision',report['visual_revision'])
  if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Fitting save failed: '+family)
  report['saved'].append(mesh.get_path_name());report['models'][family]=mesh.get_path_name()
  (O/'fitted-import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
report['status']='nine_fitted_stock_meshes_saved'
(O/'fitted-import-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('TACTICAL_STOCK_NINE_FITTINGS_SAVED '+json.dumps(report['models']))
