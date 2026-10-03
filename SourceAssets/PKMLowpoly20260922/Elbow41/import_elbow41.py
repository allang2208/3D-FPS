"""Import the Elbow41 PKM clips over the shipped animation assets.

equip + sprint_enter / sprint_loop / sprint_exit, base only.  Writes a receipt
with the on-disk package size and SHA-256 before and after, so the save is
provable rather than self-reported.
"""
import hashlib
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow41')
PKG = '/Game/Weapons/PKMLowpoly20260922'
DEST = PKG + '/Animations'
CONTENT = Path(r'D:\FPS3D\FPSGAME\Content\Weapons\PKMLowpoly20260922\Animations')
BACKUP = HERE / 'Before'
BACKUP.mkdir(exist_ok=True)

NAMES = (('A_PKM_equip', 120), ('A_PKM_sprint_enter', 120),
         ('A_PKM_sprint_loop', 120), ('A_PKM_sprint_exit', 120))
REVISION = 'Elbow41; forearm pronation ramp / elbow band de-wring (equip+sprint)'


def digest(path):
    if not path.exists():
        return None
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()[:16]}


if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing the PKM animations')

skeleton = u.load_asset(PKG + '/SK_PKM_Manny')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if not skeleton:
    raise RuntimeError('PKM geometry is required for its skeleton')
EDL = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()

flag = 'Interchange.FeatureFlags.Import.FBX'
prior = u.SystemLibrary.get_console_variable_int_value(flag)
report = {}
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    for name, fps in NAMES:
        disk = CONTENT / (name + '.uasset')
        before = digest(disk)
        backup = BACKUP / (name + '.uasset')
        if disk.exists() and not backup.exists():
            backup.write_bytes(disk.read_bytes())

        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh = False
        opt.import_animations = True
        opt.import_materials = False
        opt.import_textures = False
        opt.skeleton = skeleton.skeleton
        data = opt.anim_sequence_import_data
        data.set_editor_property('use_default_sample_rate', False)
        data.set_editor_property('custom_sample_rate', fps)

        task = u.AssetImportTask()
        task.filename = str(HERE / 'Exports' / (name + '.fbx'))
        task.destination_path = DEST
        task.destination_name = name
        task.options = opt
        task.factory = u.FbxFactory()
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        tools.import_asset_tasks([task])

        clip = u.load_asset(DEST + '/' + name)
        if not task.imported_object_paths or not clip:
            raise RuntimeError('Import failed ' + name)
        clip.set_editor_property('bone_compression_settings', compression)
        EDL.set_metadata_tag(clip, 'PKMElbowRevision', REVISION)
        if not EDL.save_loaded_asset(clip, False):
            raise RuntimeError('Save failed ' + name)
        after = digest(disk)
        report[name] = {'asset': clip.get_path_name(),
                        'seconds': clip.get_play_length(),
                        'fps': fps,
                        'before': before, 'after': after,
                        'changed': before != after}
        (HERE / 'import_receipt.json').write_text(
            json.dumps(report, indent=2), encoding='utf-8')
        u.log('PKM_ELBOW41 %s saved, changed=%s' % (name, before != after))
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(prior))

print('PKM_ELBOW41_IMPORT_COMPLETE')
for k, v in report.items():
    print('  %-22s %6.2fs  changed=%s  %s -> %s' % (
        k, v['seconds'], v['changed'],
        (v['before'] or {}).get('sha256'), (v['after'] or {}).get('sha256')))