"""Import authored sprint cycles on each current pistol skeleton. No game tests."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
root = '/Game/Weapons/PistolLocomotion20260914'
meshes = {
    'M1911': '/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny',
    'DW715': '/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny',
}
tools = u.AssetToolsHelpers.get_asset_tools()
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt = {}
for weapon, mesh_path in meshes.items():
    mesh = u.load_asset(mesh_path)
    authored = json.loads((O / weapon / 'authoring.json').read_text(encoding='utf-8'))
    for kind, info in authored['clips'].items():
        source = Path(info['fbx'])
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_animations = True
        options.skeleton = mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path = f'{root}/{weapon}/Animations'
        task.destination_name = source.stem
        task.options = options
        task.automated = True
        task.replace_existing = True
        task.save = False
        tools.import_asset_tasks([task])
        clip = u.load_asset(f'{task.destination_path}/{source.stem}')
        if not clip:
            raise RuntimeError(f'Could not import {source}')
        if compression:
            clip.set_editor_property('bone_compression_settings', compression)
        if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
            raise RuntimeError(f'Could not save {clip.get_path_name()}')
        receipt[source.stem] = clip.get_path_name()
(O / 'import.json').write_text(json.dumps({'animations': receipt, 'state': 'Imported; user testing pending'}, indent=2), encoding='utf-8')
u.log('PISTOL_LOCOMOTION_IMPORT_COMPLETE')
