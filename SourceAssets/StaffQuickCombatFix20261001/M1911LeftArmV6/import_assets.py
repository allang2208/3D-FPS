"""Import/save only the six newly authored M1911 left-arm repair animations.

Run through the project's existing editor bridge or a suitable commandlet.
This script does not start an editor, stop PIE, alter profiles, or update meshes.
"""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = '/Game/Weapons/StaffQuickCombatFix20261001/M1911/l/Animations'
manifest = json.loads((OUT / 'authoring.json').read_text(encoding='utf-8'))
receipt_path = OUT / 'import.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {
    'revision': 'M1911LeftArmV6', 'assets': [], 'runtime_tested': False}
editor = u.EditorAssetLibrary
asset_tools = u.AssetToolsHelpers.get_asset_tools()
mesh = u.load_asset('/Game/Weapons/PistolDualWield20260914/M1911/l/SK_Dual_M1911_l')
if not mesh:
    raise RuntimeError('Native left M1911 mesh is missing')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
for kind, row in manifest['clips'].items():
    name = 'A_Dual_M1911_l_' + kind
    path = ROOT + '/' + name
    if path + '.' + name in receipt['assets']:
        continue
    if editor.does_asset_exist(path):
        raise RuntimeError('Unrecorded target already exists; preserved: ' + path)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = row['fbx']
    task.destination_path = ROOT
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = options
    asset_tools.import_asset_tasks([task])
    clip = u.load_asset(path)
    if not clip:
        raise RuntimeError('Animation import did not produce asset: ' + path)
    if compression:
        clip.set_editor_property('bone_compression_settings', compression)
    editor.set_metadata_tag(clip, 'DualQuickCombat.Revision', 'M1911LeftArmV6')
    editor.set_metadata_tag(clip, 'DualQuickCombat.WristSupport', 'Full attack; idle-calibrated 22 degree target')
    if not editor.save_loaded_asset(clip, False):
        raise RuntimeError('Animation save failed: ' + path)
    receipt['assets'].append(clip.get_path_name())
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
u.log('M1911_LEFT_ARM_V6_SAVED ' + str(len(receipt['assets'])) + ' animations to ' + ROOT)
