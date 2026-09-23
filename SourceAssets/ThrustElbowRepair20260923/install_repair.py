"""Apply only the two current thrust clips; retain all other asset settings."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=Path(u.Paths.project_dir()).resolve()
patches=[(P/v/'Thrust_patch.json',json.loads((P/v/'Thrust_patch.json').read_text())) for v in ('Standard','LongGrip')]
targets={p['asset'].split('.')[0] for _,p in patches}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets&dirty:raise RuntimeError('Unsaved target changes: '+str(targets&dirty))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is active; preserve the current editor state')
for file,patch in patches:
    disk=ROOT/'Content'/(patch['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(disk.read_bytes()).hexdigest()!=patch['sha256']:raise RuntimeError('Target changed during authoring: '+patch['asset'])
receipt={'revision':'ThrustElbowSupportV1','saved':{},'gameplay_tested':False,'offline_skin_review':True}
for file,patch in patches:
    asset=u.load_asset(patch['asset']);disk=ROOT/'Content'/(patch['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
    backup=P/'Before'/file.parent.name/disk.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(disk,backup)
    controller=asset.get_editor_property('controller')
    if controller is None:
        controller=u.AnimDataController();controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('Repair bilateral thrust elbow twist with locked wrists',False)
    try:
        for n in patch['edited_bones']:
            keys=[r['bones'][n] for r in patch['samples']]
            if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
                [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],
                [u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Track rejected: '+n)
    finally:controller.close_bracket(False)
    u.EditorAssetLibrary.set_metadata_tag(asset,'ThrustElbow.Revision',patch['revision'])
    u.EditorAssetLibrary.set_metadata_tag(asset,'ThrustElbow.AuthorSource',str(file))
    u.AKMAnimationAuditLibrary.finish_animation_compression(asset)
    export=file.parent/(asset.get_name()+'.fbx')
    task=u.AssetExportTask();task.object=asset;task.filename=str(export);task.automated=True;task.prompt=False;task.replace_identical=True
    task.options=u.FbxExportOption();task.options.ascii=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('FBX export failed: '+patch['asset'])
    import_data=asset.get_editor_property('asset_import_data')
    if import_data and hasattr(import_data,'update_filename_only'):import_data.update_filename_only(str(export))
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+patch['asset'])
    receipt['saved'][file.parent.name]={'asset':asset.get_path_name(),'seconds':asset.get_play_length(),
      'backup':str(backup),'fbx':str(export),'source_sha256':patch['sha256'],'saved_sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
    receipt['status']='complete' if len(receipt['saved'])==len(patches) else 'partial'
    (P/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    u.log('THRUST_ELBOW_SAVED '+file.parent.name)
u.log('THRUST_ELBOW_INSTALL_COMPLETE')
