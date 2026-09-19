"""Import the camera-right reach/pull/return empty reload at its runtime path."""
import json
import shutil
from pathlib import Path

import unreal as u

SOURCE = Path(__file__).resolve().parent
DESTINATION = '/Game/Weapons/ASH12/ReloadReference20260919'
NAME = 'A_ASH12_reload_empty'
ASSET_PATH = DESTINATION + '/' + NAME
asset_file = SOURCE.parents[1] / 'Content/Weapons/ASH12/ReloadReference20260919' / (NAME + '.uasset')
backup = SOURCE / 'Before' / asset_file.name
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    shutil.copy2(asset_file, backup)

skeleton = u.load_asset('/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny_Skeleton')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_mesh = False
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.skeleton = skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
task = u.AssetImportTask()
task.filename = str(SOURCE / (NAME + '.fbx'))
task.destination_path = DESTINATION
task.destination_name = NAME
task.options = options
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('ASH-12 empty-reload import did not produce an asset.')
clip = u.load_asset(ASSET_PATH)
clip.set_editor_property('bone_compression_settings', compression)
if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outer()], False):
    raise RuntimeError('Could not save the edited ASH-12 empty reload.')
receipt = {'revision': 'right-edge-reach-pull-return',
           'asset': clip.get_path_name(), 'source_fbx': task.filename,
           'duration': clip.get_play_length(), 'previous_asset_copy': str(backup),
           'visual_test': 'Not run; user will assess in game.'}
(SOURCE / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_RIGHT_EDGE_IMPORT_COMPLETE ' + json.dumps(receipt))
