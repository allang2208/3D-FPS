"""Import the fourth combo hit and its counterweight rift into the sword folder.

Both swords read /Game/Weapons/AzureRunesword20260913 (items.json animation_folder),
so one import covers the rune sword and the frost crystal sword.
"""
import json
import shutil
from pathlib import Path

import unreal as u

P = Path(__file__).parent
D = '/Game/Weapons/AzureRunesword20260913'
FX = D + '/WristRiftV3'
# This case sits directly under SourceAssets, so the project root is parents[1]
# (the older rune-sword cases were one directory deeper and used parents[2]).
content = P.parents[1] / 'Content/Weapons/AzureRunesword20260913'
tools = u.AssetToolsHelpers.get_asset_tools()
receipt = []
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
skeleton = u.load_asset(D + '/SK_AzureRunesword_Manny').skeleton
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')


def task(name, options, destination):
    relative = ('WristRiftV3/' if destination == FX else '') + name + '.uasset'
    current = content / relative
    prior = P / 'Before' / relative
    if current.exists() and not prior.exists():
        prior.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current, prior)
    import_task = u.AssetImportTask()
    import_task.filename = str(P / ('Export/' + name + '.fbx'))
    import_task.destination_path = destination
    import_task.destination_name = name
    import_task.automated = True
    import_task.replace_existing = True
    import_task.save = False
    import_task.options = options
    tools.import_asset_tasks([import_task])
    asset = u.load_asset(destination + '/' + name)
    if not import_task.imported_object_paths or not asset:
        raise RuntimeError('Import failed: ' + name)
    receipt.append({'source': import_task.filename, 'asset': asset.get_path_name()})
    return asset


options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_mesh = False
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.skeleton = skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 480)
sequence = task('A_RuneSword_PommelStrike', options, D)
if compression:
    sequence.set_editor_property('bone_compression_settings', compression)
if not u.EditorAssetLibrary.save_loaded_asset(sequence):
    raise RuntimeError('Animation save failed: A_RuneSword_PommelStrike')
receipt[-1]['length_seconds'] = sequence.get_play_length()

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.auto_generate_collision = False
rift = task('SM_RuneRift_Pommel', options, FX)
rift.set_material(0, u.load_asset(FX + '/M_RuneRift'))
if not u.EditorAssetLibrary.save_loaded_asset(rift):
    raise RuntimeError('Counterweight rift save failed')

(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('RUNESWORD_POMMEL_IMPORT_COMPLETE')
