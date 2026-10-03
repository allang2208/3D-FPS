"""Import/save only this task's ten current runtime quick-melee packages."""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;PROJECT=O.parents[1]
jobs=json.loads((O/'authoring.json').read_text())
before=json.loads((O/'runtime_before.json').read_text())['clips']
receipt=json.loads((O/'import_receipt.json').read_text()) if (O/'import_receipt.json').exists() else {}
if len(jobs)!=10:raise RuntimeError('Expected both weapons and all five grip families before importing')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Active play session; preserve editor state')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,info in jobs.items():
 if key in receipt:continue
 if info['path'] in dirty:raise RuntimeError('Unsaved target animation: '+info['path'])
 old=u.load_asset(info['path'])
 if not old:raise RuntimeError('Missing runtime animation: '+info['path'])
 current=old.get_editor_property('asset_import_data').get_first_filename()
 if Path(current).resolve()!=Path(before[key+'/quick_melee']['source']).resolve():raise RuntimeError('Target was changed since inspection: '+key)
 if not Path(info['source']).exists():raise RuntimeError('Missing authored FBX: '+key)
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,info in jobs.items():
  if key in receipt:continue
  path=info['path'];old=u.load_asset(path)
  disk=PROJECT/'Content'/Path(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/Path(path.removeprefix('/Game/')+'.uasset')
  backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(disk,backup)
  skeleton=old.get_editor_property('skeleton')
  preserved={n:old.get_editor_property(n) for n in ['bone_compression_settings','curve_compression_settings','enable_root_motion','force_root_lock','root_motion_root_lock','use_normalized_root_motion_scale']}
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  d=opt.anim_sequence_import_data;d.set_editor_property('use_default_sample_rate',False);d.set_editor_property('custom_sample_rate',info['fps'])
  d.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
  task=u.AssetImportTask();task.filename=info['source'];task.destination_path=path.rsplit('/',1)[0];task.destination_name=info['name']
  task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
  A.import_asset_tasks([task])
  if not task.imported_object_paths:raise RuntimeError('Import failed: '+key)
  anim=u.load_asset(path)
  for name,value in preserved.items():anim.set_editor_property(name,value)
  E.set_metadata_tag(anim,'QuickMeleeRevision','20260924 own grips; full arm clearance; visible buttstock contact')
  if not E.save_loaded_asset(anim,False):raise RuntimeError('Save failed: '+path)
  receipt[key]={'asset':anim.get_path_name(),'saved':True,'source':info['source'],'fps':info['fps'],'duration':anim.get_play_length(),
      'before':str(backup),'before_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(Path(info['source']).read_bytes()).hexdigest(),'game_tested':False}
  (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('MELEE_SAVED',key,anim.get_play_length(),flush=True)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
print('MELEE_IMPORT_FINISHED',len(receipt),flush=True)
