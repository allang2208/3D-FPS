"""Import/save independent gesture assets; no gameplay or render execution."""
import json
from pathlib import Path

import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DEST = '/Game/Animations/LeftHandPowerFist20260923'
manifest = json.loads((P/'authoring.json').read_text(encoding='utf-8'))
mesh = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
if not mesh:
    raise RuntimeError('Current M4/Manny skeleton is unavailable')
skeleton = mesh.skeleton
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
tools = u.AssetToolsHelpers.get_asset_tools()
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
receipt = []
try:
    u.SystemLibrary.execute_console_command(None, flag+' 0')
    for clip in manifest['clips']:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.skeleton = skeleton
        options.import_mesh = False
        options.import_animations = True
        options.import_materials = False
        options.import_textures = False
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', clip['fps'])
        task = u.AssetImportTask()
        task.filename = clip['fbx']
        task.destination_path = DEST
        task.destination_name = clip['name']
        task.options = options
        task.automated = True
        task.replace_existing = False
        task.save = False
        if u.EditorAssetLibrary.does_asset_exist(DEST+'/'+clip['name']):
            raise RuntimeError('Refusing to overwrite an existing sequence: '+clip['name'])
        tools.import_asset_tasks([task])
        if not task.imported_object_paths:
            raise RuntimeError('Import produced no sequence: '+clip['name'])
        sequence = u.load_asset(task.imported_object_paths[0])
        if not sequence:
            raise RuntimeError('Imported sequence unavailable: '+clip['name'])
        if compression:
            sequence.set_editor_property('bone_compression_settings', compression)
        sequence.set_editor_property('enable_root_motion', False)
        # The loop clip is a stable pose; playback looping is chosen by its
        # eventual gameplay owner. The full gesture remains a one-shot.
        u.AKMAnimationAuditLibrary.finish_animation_compression(sequence)
        u.EditorAssetLibrary.set_metadata_tag(sequence, 'GestureFamily', manifest['revision'])
        u.EditorAssetLibrary.set_metadata_tag(sequence, 'IntendedLayerRoot', 'clavicle_l')
        u.EditorAssetLibrary.set_metadata_tag(sequence, 'SuggestedLoop', str(clip['loop']))
        u.EditorAssetLibrary.set_metadata_tag(sequence, 'FistLockedSeconds', str(manifest['fist_locked_seconds']) if clip['name'] in ('A_LeftHand_PowerFist', 'A_LeftHand_PowerFist_Raise') else '')
        if not u.EditorAssetLibrary.save_loaded_asset(sequence, False):
            raise RuntimeError('Save failed: '+clip['name'])
        receipt.append({'asset': sequence.get_path_name(), 'source': task.filename,
                        'saved': True, 'skeleton': skeleton.get_path_name(),
                        'duration': clip['duration'], 'suggested_loop': clip['loop']})
        (P/'import_receipt.json').write_text(json.dumps({
            'status': 'complete' if len(receipt) == len(manifest['clips']) else 'partial',
            'assets': receipt, 'gameplay_hook_added': False, 'tests_or_renders_run': False,
        }, indent=2), encoding='utf-8')
        u.log('POWER_FIST_SAVED '+sequence.get_path_name())
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))
u.log('POWER_FIST_IMPORT_COMPLETE')
