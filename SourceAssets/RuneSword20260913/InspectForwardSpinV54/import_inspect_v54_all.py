"""Reimport V54 inspect into every live sword animation folder and report lengths."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = P.parents[2]
SOURCE = str(P / 'ExportV79' / 'A_RuneSword_Inspect.fbx')
NAME = 'A_RuneSword_Inspect'
DESTS = [
    '/Game/Weapons/AzureRunesword20260913',
    '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',
]
MESH = '/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'
COMPRESSION = '/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'
FLAG = 'Interchange.FeatureFlags.Import.FBX'


def content_file(dest):
    rel = dest.replace('/Game/', 'Content/')
    return ROOT / rel / (NAME + '.uasset')


def import_one(dest):
    current = content_file(dest)
    backup = P / 'BeforeV54' / dest.replace('/Game/', '').replace('/', '_') / (NAME + '.uasset')
    if current.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current, backup)
    mesh = u.load_asset(MESH)
    compression = u.load_asset(COMPRESSION)
    ui = u.FbxImportUI()
    ui.automated_import_should_detect_type = False
    ui.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    ui.import_mesh = False
    ui.import_animations = True
    ui.import_materials = False
    ui.import_textures = False
    ui.skeleton = mesh.skeleton
    ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    ui.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = SOURCE
    task.destination_path = dest
    task.destination_name = NAME
    is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    task.automated = True
    task.replace_existing = True
    task.save = is_commandlet
    task.options = ui
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sequence = u.load_asset(dest + '/' + NAME)
    if not task.imported_object_paths or not sequence:
        raise RuntimeError('import failed ' + dest)
    if compression:
        sequence.set_editor_property('bone_compression_settings', compression)
    if hasattr(sequence, 'clear_compressed_stats'):
        sequence.clear_compressed_stats()
    sequence.modify()
    saved = u.EditorAssetLibrary.save_asset(dest + '/' + NAME, False)
    if not saved:
        packages = [sequence.get_package()]
        saved = bool(u.EditorLoadingAndSavingUtils.save_packages(packages, False))
    if not saved:
        raise RuntimeError('save failed ' + dest + ' duration=' + str(sequence.get_play_length()))
    return {
        'path': sequence.get_path_name(),
        'duration': sequence.get_play_length(),
        'imported': list(task.imported_object_paths),
        'disk': str(current),
        'disk_bytes': current.stat().st_size if current.exists() else 0,
    }


previous = u.SystemLibrary.get_console_variable_int_value(FLAG)
rows = []
try:
    u.SystemLibrary.execute_console_command(None, FLAG + ' 0')
    for dest in DESTS:
        rows.append(import_one(dest))
finally:
    u.SystemLibrary.execute_console_command(None, f'{FLAG} {previous}')

(P / 'import_receipt_v54_all.json').write_text(json.dumps({
        'revision': 'InspectForwardSpinV79',
    'folders': rows,
    'testing': 'No gameplay, PIE or acceptance run; user tests.',
}, indent=2), encoding='utf-8')
u.log('INSPECT_V54_ALL %s' % ', '.join('%.3fs %s' % (r['duration'], r['path']) for r in rows))
