"""Import the authored dual quick-combat clips into the open editor.

Run through Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript.
Uses the skeleton belonging to each existing dual mesh; does not change meshes.
"""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent / globals().get('MOTION_REVISION', '')
assets = u.AssetToolsHelpers.get_asset_tools()
editor = u.EditorAssetLibrary
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
receipt = {'revision': globals().get('MOTION_REVISION', 'V1'),
           'assets': [], 'testing': 'Not performed; user testing'}
for weapon in ('M1911', 'DW715'):
    manifest = json.loads((OUT / f'{weapon}-authoring.json').read_text(encoding='utf-8'))
    for side, entry in manifest['sides'].items():
        mesh_path = f'/Game/Weapons/PistolDualWield20260914/{weapon}/{side}/SK_Dual_{weapon}_{side}'
        mesh = u.load_asset(mesh_path)
        if not mesh:
            raise RuntimeError('Missing existing dual mesh: ' + mesh_path)
        revision = globals().get('DESTINATION_REVISION', '')
        root = '/Game/Weapons/DualPistolQuickCombat20260920'
        if revision:
            root += '/' + revision
        destination = f'{root}/{weapon}/{side}/Animations'
        for kind, clip_info in entry['clips'].items():
            name = f'A_Dual_{weapon}_{side}_{kind}'
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh = False
            options.import_animations = True
            options.import_materials = False
            options.import_textures = False
            options.skeleton = mesh.skeleton
            options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
            options.anim_sequence_import_data.set_editor_property('custom_sample_rate', manifest['sample_rate'])
            task = u.AssetImportTask()
            task.filename = clip_info['fbx']
            task.destination_path = destination
            task.destination_name = name
            task.automated = True
            task.replace_existing = True
            task.save = False
            task.options = options
            # Resume a completed in-memory import after a save was blocked by PIE.
            if name not in globals().get('ALREADY_IMPORTED', ()):
                assets.import_asset_tasks([task])
            clip = u.load_asset(destination + '/' + name)
            if not clip:
                raise RuntimeError('Animation import failed: ' + name)
            if compression:
                clip.set_editor_property('bone_compression_settings', compression)
            if not editor.save_loaded_asset(clip, False):
                raise RuntimeError('Animation save failed: ' + name)
            receipt['assets'].append(clip.get_path_name())
            (OUT / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            u.log('DUAL_QUICKCOMBAT_SAVED ' + clip.get_path_name())
u.log('DUAL_QUICKCOMBAT_IMPORT_COMPLETE')
