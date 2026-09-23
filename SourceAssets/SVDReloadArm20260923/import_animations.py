"""Import only the ten revised reload assets at their current runtime paths."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/SVDReloadArm20260923');PROJECT=O.parents[1]
auth=json.loads((O/'authoring.json').read_text());receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {}
jobs=[(k,a) for k,a in auth.items() if k not in receipt]
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active play session: preserve state; no animation import')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts=[a['path'] for _,a in jobs if a['path'] in dirty]
if conflicts:raise RuntimeError('Unsaved target animations: '+str(conflicts))
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in jobs:
  path=info['path'];old=u.load_asset(path);source=Path(info['source'])
  if not old or not source.exists():raise RuntimeError('Missing animation input '+path)
  disk=PROJECT/'Content'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup=O/'Before'/Path(path.removeprefix('/Game/')).with_suffix('.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(disk,backup)
  compression=old.get_editor_property('bone_compression_settings');skeleton=old.get_editor_property('skeleton')
  preserved={n:old.get_editor_property(n) for n in ['enable_root_motion','force_root_lock','root_motion_root_lock','use_normalized_root_motion_scale']}
  opts=u.FbxImportUI();opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opts.skeleton=skeleton
  opts.import_mesh=False;opts.import_animations=True;opts.import_materials=False;opts.import_textures=False
  opts.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  t=u.AssetImportTask();t.filename=str(source);t.destination_path=path.rsplit('/',1)[0];t.destination_name=info['name'];t.options=opts;t.factory=u.FbxFactory();t.automated=True;t.replace_existing=True;t.replace_existing_settings=False;t.save=False
  A.import_asset_tasks([t])
  if not t.imported_object_paths:raise RuntimeError('Animation import failed '+path)
  anim=u.load_asset(path);anim.set_editor_property('bone_compression_settings',compression)
  for name,value in preserved.items():anim.set_editor_property(name,value)
  if not E.save_loaded_asset(anim,False):raise RuntimeError('Animation save failed '+path)
  receipt[key]={'asset':anim.get_path_name(),'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'saved':True,'before':str(backup),'game_tested':False}
  (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVD_ARM_ANIMATION_SAVED',key,flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('SVD_ARM_ANIMATION_IMPORT_COMPLETE',len(receipt),flush=True)
