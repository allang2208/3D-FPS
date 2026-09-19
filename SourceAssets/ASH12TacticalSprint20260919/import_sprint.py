"""Import only the three new ASH-12 sprint sequences on the existing skeleton."""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
DEST = '/Game/Weapons/ASH12/TacticalSprint20260919'
mesh = u.load_asset('/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
asset_tools = u.AssetToolsHelpers.get_asset_tools()
receipt = {}
for kind in ('Enter', 'Loop', 'Exit'):
    name = 'A_ASH12_TacticalSprint_' + kind
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
    task.filename = str(HERE / 'Animations' / (name + '.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    asset_tools.import_asset_tasks([task])
    clip = u.load_asset(DEST + '/' + name)
    if not clip:
        raise RuntimeError('Sprint import failed: ' + name)
    clip.set_editor_property('bone_compression_settings', compression)
    if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError('Sprint save failed: ' + name)
    receipt[kind] = {'asset': clip.get_path_name(), 'duration': clip.get_play_length()}
    u.log('ASH12_SPRINT_IMPORTED ' + json.dumps(receipt[kind]))
(HERE / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ASH12_TACTICAL_SPRINT_IMPORT_COMPLETE')
