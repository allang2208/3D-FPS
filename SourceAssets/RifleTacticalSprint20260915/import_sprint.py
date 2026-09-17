"""Import authored rifle sprint animations onto each rifle's current skeleton."""
import json
import os
import sys
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
root = '/Game/Weapons/RifleTacticalSprint20260915'
specs = json.loads((O / 'sources.json').read_text(encoding='utf-8'))
# The pythonscript commandlet does not forward custom argv; select a weapon
# with RIFLE_SPRINT_ONLY=<Weapon> (or ALL) when partial re-import is needed.
only = os.environ.get('RIFLE_SPRINT_ONLY') or (sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else None)
if only in (None, 'ALL'):
    only = None
asset_tools = u.AssetToolsHelpers.get_asset_tools()
receipt_path = O / 'import.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))['animations'] if receipt_path.exists() else {}
for weapon, spec in specs.items():
    if only and weapon != only:
        continue
    mesh = u.load_asset(spec['mesh'])
    compression = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/BC_AKM_GripPrecision'
        if weapon == 'AKM' else '/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    for profile in spec['profiles']:
        authored = json.loads((O / weapon / profile / 'authoring.json').read_text(encoding='utf-8'))
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
            task.destination_path = f'{root}/{weapon}/{profile}'
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
            u.log(f'RIFLE_SPRINT_SAVED {source.stem}')
(O / 'import.json').write_text(json.dumps({'animations': receipt,
    'status': 'Imported and saved; user testing pending',
    'partial': only or 'all'}, indent=2), encoding='utf-8')
u.log('RIFLE_TACTICAL_SPRINT_IMPORT_COMPLETE')
