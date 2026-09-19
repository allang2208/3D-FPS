"""Import only the authored M4 tactical sprint clips; no runtime checks."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
root = '/Game/Weapons/M4TacticalSprint20260915'
mesh = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
asset_tools = u.AssetToolsHelpers.get_asset_tools()
receipt = {}
for profile in ('Base', 'Drum', 'Angled', 'Vertical', 'Canted', 'Prism'):
    authored = json.loads((O / profile / 'authoring.json').read_text(encoding='utf-8'))
    for kind, info in authored['clips'].items():
        source = Path(info['fbx'])
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
        task.filename = str(source)
        task.destination_path = f'{root}/{profile}'
        task.destination_name = source.stem
        task.options = options
        task.automated = True
        task.replace_existing = True
        task.save = False
        asset_tools.import_asset_tasks([task])
        clip = u.load_asset(f'{task.destination_path}/{source.stem}')
        if not clip:
            raise RuntimeError(f'Import failed: {source}')
        clip.set_editor_property('bone_compression_settings', compression)
        if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
            raise RuntimeError(f'Save failed: {clip.get_path_name()}')
        receipt[source.stem] = clip.get_path_name()
(O / 'import.json').write_text(json.dumps({'animations': receipt,
    'status': 'Imported and saved; user testing pending'}, indent=2), encoding='utf-8')
u.log('M4_TACTICAL_SPRINT_IMPORT_COMPLETE')
