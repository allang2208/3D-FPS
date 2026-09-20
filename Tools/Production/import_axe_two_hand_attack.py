"""Import only the axe's two-hand Swing and HitRecover into their runtime paths.

Run in the active editor via ue_python_exec.py, or by commandlet when it is closed.
The mesh, materials and H4 grip asset are left intact. No playback or tests.
"""
import json
import shutil
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/AxeRightArm20260919'
RECOVERY = SOURCE
config = json.loads((SOURCE / 'authoring.json').read_text(encoding='utf-8'))
DEST = '/Game/Items/ProductionTools/GripMotion20260913'
targets = {DEST + '/A_Harvest_Axe_' + clip for clip in ('Swing', 'HitRecover')}
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before importing the axe right arm. No assets changed.')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name() in targets]
if dirty:
    raise RuntimeError('Axe animation has unsaved editor changes: ' + ', '.join(dirty))
backup = SOURCE / 'Before'
backup.mkdir(parents=True, exist_ok=True)
for clip in ('Swing', 'HitRecover'):
    file = 'A_Harvest_Axe_' + clip + '.uasset'
    previous = ROOT / 'Content/Items/ProductionTools/GripMotion20260913' / file
    if previous.exists() and not (backup / file).exists():
        shutil.copy2(previous, backup / file)
mesh = u.load_asset(DEST + '/SK_Harvest_Axe')
skeleton = mesh.get_editor_property('skeleton')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
receipt = {'runtime_tested': False, 'rendered': False, 'revision': config['revision'], 'saved': []}
for clip in ('Swing', 'HitRecover'):
    name = 'A_Harvest_Axe_' + clip
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', config['fps'])
    task = u.AssetImportTask()
    task.filename = str((RECOVERY if clip == 'HitRecover' else SOURCE) / 'Export' / (name + '.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    animation = u.load_asset(DEST + '/' + name)
    if compression:
        animation.set_editor_property('bone_compression_settings', compression)
    if not u.EditorAssetLibrary.save_loaded_asset(animation, False):
        raise RuntimeError('Could not save ' + name)
    receipt['saved'].append(animation.get_path_name())
(SOURCE / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt, indent=2))
u.log('AXE_TWO_HAND_ATTACK_IMPORTED')
