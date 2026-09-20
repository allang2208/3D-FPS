"""Import H4/V5 with the thumb correction and delayed recovery in the stopped editor.

No playback or runtime checks. Back up only the four replaced animation assets.
"""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
HOLD = ROOT / 'SourceAssets/AxeThumb20260919/Fixed'
ATTACK = ROOT / 'SourceAssets/AxeRightArm20260919'
RECOVERY = ATTACK
DEST = '/Game/Items/ProductionTools/GripMotion20260913'
CLIPS = {'Idle': (HOLD, 150), 'Equip': (HOLD, 150),
         'Swing': (ATTACK, 300), 'HitRecover': (RECOVERY, 300)}
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before importing the axe pose family. No assets changed.')
targets = {DEST + '/A_Harvest_Axe_' + clip for clip in CLIPS}
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name() in targets]
if dirty:
    raise RuntimeError('Axe animation has unsaved editor changes: ' + ', '.join(dirty))
backup = HOLD / 'Before'
backup.mkdir(parents=True, exist_ok=True)
for clip in CLIPS:
    filename = 'A_Harvest_Axe_' + clip + '.uasset'
    previous = ROOT / 'Content/Items/ProductionTools/GripMotion20260913' / filename
    if previous.exists() and not (backup / filename).exists():
        shutil.copy2(previous, backup / filename)
mesh = u.load_asset(DEST + '/SK_Harvest_Axe')
skeleton = mesh.get_editor_property('skeleton')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
receipt = {'revision': 'H4_V5_ThumbFix1_HitPause200ms_RightElbow1', 'runtime_tested': False, 'rendered': False, 'saved': []}
for clip, (source, fps) in CLIPS.items():
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
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', fps)
    task = u.AssetImportTask()
    task.filename = str(source / 'Export' / (name + '.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import did not produce ' + name)
    animation = u.load_asset(DEST + '/' + name)
    if compression:
        animation.set_editor_property('bone_compression_settings', compression)
    if not u.EditorAssetLibrary.save_loaded_asset(animation, False):
        raise RuntimeError('Could not save ' + name)
    receipt['saved'].append(animation.get_path_name())
    (HOLD / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt, indent=2))
u.log('AXE_THUMB_POSE_FAMILY_IMPORTED')
