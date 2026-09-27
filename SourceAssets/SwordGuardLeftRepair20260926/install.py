"""Save the six guard animations, preserving their native frame grids/timing."""
import unreal as u,json,hashlib
from pathlib import Path
P=Path(__file__).parent;ROOT=Path(u.Paths.project_dir()).resolve()
patches=[(f,json.loads(f.read_text())) for v in ('Standard','LongGrip') for f in sorted((P/'Final'/v).glob('*_patch.json'))]
receipt_path=P/'import_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'revision':'GuardCameraPlaneV22','assets':{},'runtime_tested':False}
dirty={str(p.get_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for f,p in patches:
    key=f.parent.name+'/'+f.stem;disk=ROOT/'Content'/(p['asset'].removeprefix('/Game/')+'.uasset')
    expected=receipt['assets'][key]['after_sha256'] if key in receipt['assets'] else p['source_sha256']
    if hashlib.sha256(disk.read_bytes()).hexdigest()!=expected:raise RuntimeError('Target changed; retained: '+p['asset'])
    if p['asset'] in dirty:raise RuntimeError('Unsaved target retained: '+p['asset'])
for f,p in patches:
    key=f.parent.name+'/'+f.stem
    if key in receipt['assets']:continue
    asset=u.load_asset(p['asset']);model=asset.get_editor_property('data_model_interface')
    if model.get_number_of_frames()!=p['intervals']:raise RuntimeError('Native grid changed')
    controller=asset.get_editor_property('controller');controller.open_bracket('Camera-plane guard with supported arms',False)
    try:
        for n in p['edited_bones']:
            keys=[r['bones'][n] for r in p['samples']]
            if not controller.set_bone_track_keys(n,[u.Vector(*k['p']) for k in keys],
                [u.Quat(k['q'][1],k['q'][2],k['q'][3],k['q'][0]) for k in keys],[u.Vector(*k['s']) for k in keys],False):
                raise RuntimeError('Cannot write '+n)
    finally:controller.close_bracket(False)
    u.EditorAssetLibrary.set_metadata_tag(asset,'SwordGuard.Revision','GuardCameraPlaneV22')
    u.EditorAssetLibrary.set_metadata_tag(asset,'SwordGuard.AuthorSource',str(f))
    export=u.AssetExportTask();export.object=asset;export.filename=str(f.parent/(asset.get_name()+'.fbx'))
    export.automated=True;export.prompt=False;export.replace_identical=True;export.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(export):raise RuntimeError('Final FBX export failed')
    source=asset.get_editor_property('asset_import_data')
    if source:source.scripted_add_filename(export.filename,0,'Guard V22 native tracks')
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed')
    disk=ROOT/'Content'/(p['asset'].removeprefix('/Game/')+'.uasset')
    receipt['assets'][key]={'asset':p['asset'],'saved':True,'intervals':model.get_number_of_frames(),'seconds':asset.get_play_length(),
        'before_sha256':p['source_sha256'],'after_sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'final_fbx':export.filename,'keys':str(f)}
    receipt_path.write_text(json.dumps(receipt,indent=2))
    print('GUARD_V22_SAVED',key,flush=True)
