"""Install authored bone tracks on the existing standard/long-grip assets."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=Path(u.Paths.project_dir()).resolve()
patches=[(f,json.loads(f.read_text())) for v in ('Standard','LongGrip') for f in sorted((P/v).glob('*_patch.json'))]
receipt_path=P/'import_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'revision':'SwordWristLockedV4','saved':{},'runtime_tested':False}
targets={p['asset'].split('.')[0] for _,p in patches}
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
 raise RuntimeError('PIE is active; target animations preserved. End play before installing the repair.')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:raise RuntimeError('Unsaved edits on target assets: '+str(dirty))
for file,patch in patches:
 key=file.parent.name+'/'+file.stem
 if key in receipt['saved']:continue
 disk=ROOT/'Content'/(patch['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=patch['source_sha256']:
  raise RuntimeError('Target changed since authoring; no overwrite: '+patch['asset'])
for file,patch in patches:
 key=file.parent.name+'/'+file.stem
 if key in receipt['saved']:continue
 asset=u.load_asset(patch['asset']);disk=ROOT/'Content'/(patch['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
 backup=P/'Before'/file.parent.name/disk.name;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(disk,backup)
 controller=asset.get_editor_property('controller')
 if controller is None:
  controller=u.AnimDataController();controller.set_model(asset.get_editor_property('data_model_interface'))
 controller.open_bracket('Preserve prior wrist approach and support proximal elbows',False)
 try:
  for n in patch['edited_bones']:
   keys=[r['bones'][n] for r in patch['samples']]
   if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
     [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
    raise RuntimeError('Failed bone track '+n+' in '+patch['asset'])
 finally:controller.close_bracket(False)
 u.EditorAssetLibrary.set_metadata_tag(asset,'SwordElbow.Revision','WristLockedV4')
 u.EditorAssetLibrary.set_metadata_tag(asset,'SwordElbow.AuthorSource',str(file))
 export=file.parent/(asset.get_name()+'.fbx')
 task=u.AssetExportTask();task.object=asset;task.filename=str(export);task.automated=True;task.prompt=False;task.replace_identical=True
 task.options=u.FbxExportOption();task.options.ascii=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Editable FBX export failed '+patch['asset'])
 import_data=asset.get_editor_property('asset_import_data')
 if import_data and hasattr(import_data,'update_filename_only'):import_data.update_filename_only(str(export))
 if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+patch['asset'])
 receipt['saved'][key]={'asset':asset.get_path_name(),'seconds':asset.get_play_length(),'backup':str(backup),'source_sha256':patch['source_sha256'],'editable_keys':str(file),'fbx':str(export)}
 receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
 u.log('SWORD_WRIST_LOCKED_IMPORTED '+key)
