"""Install six authored guard clips in place and save their native FBX sources."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = Path(u.Paths.project_dir()).resolve()
patches = [(f, json.loads(f.read_text())) for variant in ('Standard', 'LongGrip')
           for f in sorted((P / variant).glob('*_patch.json'))]
receipt_path = P / 'import_receipt.json'
receipt = {'revision': 'OpenPalmGuard20260926', 'saved': [], 'runtime_tested': False, 'rendered': False}
targets = {p['asset'] for _, p in patches}
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:
    raise RuntimeError('Target has unsaved edits: '+str(dirty))
for file, patch in patches:
    disk = ROOT / 'Content' / (patch['asset'].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(disk.read_bytes()).hexdigest() != patch['source_sha256']:
        raise RuntimeError('Target changed since the authoring read: '+patch['asset'])

for file, patch in patches:
    asset = u.load_asset(patch['asset'])
    disk = ROOT / 'Content' / (patch['asset'].removeprefix('/Game/')+'.uasset')
    backup = P / 'Before' / file.parent.name / disk.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk, backup)
    controller = asset.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(asset.get_editor_property('data_model_interface'))
    controller.open_bracket('Inward sword guard with open palm and supported elbow', False)
    try:
        for name in patch['edited_bones']:
            keys = [s['bones'][name] for s in patch['samples']]
            positions = [u.Vector(*k['p']) for k in keys]
            rotations = [u.Quat(k['q'][1], k['q'][2], k['q'][3], k['q'][0]) for k in keys]
            scales = [u.Vector(*k['s']) for k in keys]
            if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                raise RuntimeError('Failed to author track '+name+' in '+patch['asset'])
    finally:
        controller.close_bracket(False)
    u.EditorAssetLibrary.set_metadata_tag(asset, 'MeleeGuard.Revision', patch['revision'])
    u.EditorAssetLibrary.set_metadata_tag(asset, 'MeleeGuard.AuthorSource', str(file))
    export = file.parent / (asset.get_name()+'.fbx')
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(export)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.options = u.FbxExportOption()
    task.options.ascii = False
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Native animation FBX export failed: '+patch['asset'])
    import_data = asset.get_editor_property('asset_import_data')
    import_data.scripted_add_filename(str(export), 0, 'Open-palm guard native animation')
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: '+patch['asset'])
    receipt['saved'].append({'asset': asset.get_path_name(), 'seconds': patch['seconds'],
                             'native_fbx': str(export), 'editable_tracks': str(file),
                             'backup': str(backup), 'source_sha256': patch['source_sha256']})
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('OPEN_PALM_GUARD_SAVED '+file.parent.name+' '+asset.get_name())
print('OPEN_PALM_GUARD_INSTALL_COMPLETE')
