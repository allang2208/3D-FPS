"""Save the ten repaired SVD reload animations into their existing runtime paths.

Keeps every other channel, the skeleton, compression settings and root-motion flags.
A rollback copy of each current package is taken before the first overwrite.
"""
import json, hashlib, shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
PROJECT = O.parents[1]
FAMILIES = ['base', 'vertical', 'canted', 'prism', 'angled']
ROOT = '/Game/Weapons/SVDDragunov20260922'
COMPLETE = ROOT + '/Complete20260923/Animations'
ACCESSORIES = ROOT + '/Accessories20260923/Animations'

jobs = {}
for family in FAMILIES:
    prefix = '' if family == 'base' else family + '_'
    for clip in ('reload', 'reload_empty'):
        key = f'{family}/{clip}'
        report = json.loads((O / f'authoring_{family}_{clip}.json').read_text())[key]
        name = f'A_SVD_{prefix}{clip}'
        folder = COMPLETE if family == 'base' else ACCESSORIES
        jobs[key] = dict(path=f'{folder}/{name}', name=name, source=report['fbx'],
                         frames=report['frames'], fps=120, params=report['params'])

receipt_path = O / 'import_receipt.json'
receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Active play session; preserve it')
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def disk_path(path):
    return PROJECT / 'Content' / Path(path.removeprefix('/Game/') + '.uasset')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


for key, info in jobs.items():
    if key in receipt:
        continue
    if info['path'] in dirty:
        raise RuntimeError('Unsaved target animation: ' + info['path'])
    if not Path(info['source']).exists():
        raise RuntimeError('Missing authored FBX: ' + key)

E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
flag = 'Interchange.FeatureFlags.Import.FBX'
prior = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    for key, info in jobs.items():
        if key in receipt:
            continue
        path = info['path']
        old = u.load_asset(path)
        if not old:
            raise RuntimeError('Missing runtime animation: ' + path)
        disk = disk_path(path)
        backup = O / 'Before' / Path(path.removeprefix('/Game/') + '.uasset')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(disk, backup)
        previous_source = ''
        try:
            previous_source = old.get_editor_property('asset_import_data').get_first_filename()
        except Exception:
            pass
        skeleton = old.get_editor_property('skeleton')
        preserved = {n: old.get_editor_property(n) for n in
                     ['bone_compression_settings', 'curve_compression_settings', 'enable_root_motion',
                      'force_root_lock', 'root_motion_root_lock', 'use_normalized_root_motion_scale']}
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False
        opt.import_animations = True
        opt.import_materials = False
        opt.import_textures = False
        opt.skeleton = skeleton
        data = opt.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate', False)
        data.set_editor_property('custom_sample_rate', info['fps'])
        data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        task = u.AssetImportTask()
        task.filename = info['source']
        task.destination_path = path.rsplit('/', 1)[0]
        task.destination_name = info['name']
        task.options = opt
        task.factory = u.FbxFactory()
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        A.import_asset_tasks([task])
        if not task.imported_object_paths:
            raise RuntimeError('Import failed: ' + key)
        anim = u.load_asset(path)
        for name, value in preserved.items():
            anim.set_editor_property(name, value)
        E.set_metadata_tag(anim, 'LeftArmCameraProtection',
                           '20260925 reload tail: support-arm root relocated outside the eye volume, '
                           'wrist contact and bone lengths preserved, frames %d-%d' % (274, 344))
        if not E.save_loaded_asset(anim, False):
            raise RuntimeError('Save failed: ' + path)
        receipt[key] = dict(asset=anim.get_path_name(), saved=True, source=info['source'],
                            previous_source=previous_source, params=info['params'],
                            duration=anim.get_play_length(),
                            before=str(backup), before_sha256=sha(backup),
                            source_sha256=sha(info['source']), saved_sha256=sha(disk),
                            game_tested=False)
        receipt_path.write_text(json.dumps(receipt, indent=2))
        print('SVD_LEFT_ARM_SAVED', key, anim.get_play_length(), flush=True)
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(prior))
print('SVD_LEFT_ARM_IMPORT_COMPLETE', len(receipt), flush=True)
