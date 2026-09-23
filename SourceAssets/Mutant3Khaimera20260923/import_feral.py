"""Import the authored animations into the isolated project using the original skeleton."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).parent
DEST = '/Game/Monsters/Mutant3Meshy/KhaimeraV1/Animations'
contract = json.loads((ROOT/'animation_contract.json').read_text())
mesh = u.load_asset('/Game/Monsters/Mutant3Meshy/SK_Mutant3_Meshy')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
delivery = {}
for role, info in contract['clips'].items():
    name = 'A_Mutant3_'+role
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_as_skeletal = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    data = options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', 60)
    data.set_editor_property('convert_scene_unit', True)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    task.filename = str(ROOT/'final'/(name+'.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.options = options
    task.automated = True
    task.save = True
    task.replace_existing = True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import did not produce an animation: '+name)
    clip = u.load_asset(DEST+'/'+name)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('loop', info['loop'])
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    lib = u.EditorAssetLibrary
    lib.set_metadata_tag(clip, 'Source', 'Epic Games Paragon Khaimera / '+info['source'])
    lib.set_metadata_tag(clip, 'SourceURL', contract['source_url'])
    lib.set_metadata_tag(clip, 'Revision', 'Mutant3 Khaimera V1 2026-09-23')
    lib.set_metadata_tag(clip, 'Status', 'Authored and saved; user runtime review pending')
    if not lib.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save '+name)
    delivery[role] = dict(asset=clip.get_path_name(), **info)
contract['skeleton'] = mesh.skeleton.get_path_name()
contract['state'] = 'Nine animations imported and saved in isolated UE project; no gameplay or visual acceptance performed'
(ROOT/'animation_contract.json').write_text(json.dumps(contract, indent=2), encoding='utf-8')
(ROOT/'import_delivery.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
u.log('MUTANT3_FERAL_IMPORTED '+str(len(delivery)))
