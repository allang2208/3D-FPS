"""Import the V47 rune-sword inspection (V46 arms plus the rebuilt twirl)."""
import json
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = P.parents[2]
DEST = '/Game/Weapons/AzureRunesword20260913'
NAME = 'A_RuneSword_Inspect'
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
current = ROOT / 'Content/Weapons/AzureRunesword20260913' / (NAME + '.uasset')
backup = P / 'BeforeV47' / (NAME + '.uasset')
if current.exists() and not backup.exists():
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(current, backup)
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    mesh = u.load_asset(DEST + '/SK_AzureRunesword_Manny')
    compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
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
    task.filename = str(P / 'ExportV47' / (NAME + '.fbx'))
    task.destination_path = DEST
    task.destination_name = NAME
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = ui
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sequence = u.load_asset(DEST + '/' + NAME)
    if not task.imported_object_paths or not sequence:
        raise RuntimeError('Animation import failed: ' + NAME)
    if compression:
        sequence.set_editor_property('bone_compression_settings', compression)
    if not u.EditorAssetLibrary.save_loaded_asset(sequence):
        raise RuntimeError('Animation save failed: ' + NAME)
    (P / 'import_receipt_v47.json').write_text(json.dumps({
        'revision': 'InspectTwirlV47',
        'asset': sequence.get_path_name(), 'source': task.filename,
        'duration': sequence.get_play_length(), 'saved': True,
        'previous_asset_backup': str(backup),
        'runtime_entry': 'Existing URuneSwordComponent::BeginInspect -> A_RuneSword_Inspect',
        'scope': 'Rune sword Inspect animation only',
        'testing': 'No gameplay, PIE, render or acceptance run performed; user tests.'
    }, indent=2), encoding='utf-8')
    u.log('INSPECT_TWIRL_V47_IMPORT_COMPLETE')
finally:
    u.SystemLibrary.execute_console_command(None, f'{flag} {previous}')
