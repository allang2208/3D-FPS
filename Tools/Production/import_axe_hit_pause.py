"""Import only the axe's delayed lodged recovery; do not run playback/tests."""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/AxeRightArm20260919'
DEST = '/Game/Items/ProductionTools/GripMotion20260913'
NAME = 'A_Harvest_Axe_HitRecover'
target = DEST + '/' + NAME
# A Python commandlet has no level-editor instance; querying PIE there crashes
# inside LevelEditor. The live-editor path still requires the user to stop PIE.
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before importing the axe recovery. No assets changed.')
if any(p.get_name() == target for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('The axe recovery has unsaved editor changes: ' + target)
backup = SOURCE / 'Before'
backup.mkdir(parents=True, exist_ok=True)
previous = ROOT / 'Content/Items/ProductionTools/GripMotion20260913' / (NAME + '.uasset')
if previous.exists() and not (backup / previous.name).exists():
    shutil.copy2(previous, backup / previous.name)
mesh = u.load_asset(DEST + '/SK_Harvest_Axe')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_mesh = False
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.skeleton = mesh.get_editor_property('skeleton')
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 300)
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
task = u.AssetImportTask()
task.filename = str(SOURCE / 'Export' / (NAME + '.fbx'))
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = True
task.options = options
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Import did not produce ' + NAME)
animation = u.load_asset(target)
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if compression:
    animation.set_editor_property('bone_compression_settings', compression)
if not u.EditorAssetLibrary.save_loaded_asset(animation, False):
    raise RuntimeError('Could not save ' + target)
receipt = {'revision': 'H4_V5_ThumbFix1_HitPause200ms_RightElbow1',
           'saved': [str(path) for path in task.imported_object_paths], 'runtime_tested': False, 'rendered': False}
(SOURCE / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('AXE_HIT_PAUSE_IMPORTED ' + target)
