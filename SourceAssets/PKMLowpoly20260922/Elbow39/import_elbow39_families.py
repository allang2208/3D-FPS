"""Import the Elbow39 PKM clips for the four grip/optic families.

Same pronation re-timing as the base clips, exported from each family's own
editable blend.  No PIE or runtime tests; per-asset hash receipts prove the save.
"""
import hashlib
import json
from pathlib import Path

import unreal as u

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow39')
PKG = '/Game/Weapons/PKMLowpoly20260922'
CONTENT = Path(r'D:\FPS3D\FPSGAME\Content\Weapons\PKMLowpoly20260922')
BACKUP = HERE / 'Before' / 'families'
BACKUP.mkdir(parents=True, exist_ok=True)
REVISION = 'Elbow39; forearm pronation ramp / elbow band de-wring'

FAMILIES = ('angled', 'canted', 'prism', 'vertical')
CLIPS = (('idle', 60), ('reload', 120), ('reload_empty', 120))


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
    for family in FAMILIES:
        for clip, fps in CLIPS:
            name = 'A_PKM_%s_%s' % (family, clip)
            dest = PKG + '/Accessories14/Animations/' + family
            disk = CONTENT / 'Accessories14' / 'Animations' / family / (name + '.uasset')
            before = digest(disk)
            backup = BACKUP / family / (name + '.uasset')
            backup.parent.mkdir(parents=True, exist_ok=True)
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
            task.filename = str(HERE / 'Exports' / family / (name + '.fbx'))
            task.destination_path = dest
            task.destination_name = name
            task.options = opt
            task.factory = u.FbxFactory()
            task.automated = True
            task.replace_existing = True
            task.replace_existing_settings = True
            task.save = False
            tools.import_asset_tasks([task])

            asset = u.load_asset(dest + '/' + name)
            if not task.imported_object_paths or not asset:
                raise RuntimeError('Import failed ' + name)
            asset.set_editor_property('bone_compression_settings', compression)
            EDL.set_metadata_tag(asset, 'PKMElbowRevision', REVISION)
            if not EDL.save_loaded_asset(asset, False):
                raise RuntimeError('Save failed ' + name)
            after = digest(disk)
            report[name] = {'asset': asset.get_path_name(),
                            'seconds': asset.get_play_length(),
                            'before': before, 'after': after,
                            'changed': before != after}
            (HERE / 'import_receipt_families.json').write_text(
                json.dumps(report, indent=2), encoding='utf-8')
            u.log('PKM_ELBOW39_FAMILY %s saved, changed=%s' % (name, before != after))
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(prior))

print('PKM_ELBOW39_FAMILY_IMPORT_COMPLETE')
for k, v in report.items():
    print('  %-30s %6.2fs  changed=%s' % (k, v['seconds'], v['changed']))