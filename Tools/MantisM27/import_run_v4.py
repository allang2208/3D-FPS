"""Import/save M27 hunched locomotion and connect the existing post-aggro state."""
from pathlib import Path
import json
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/RunV4')
SOURCE = ROOT / 'Delivery'
DEST = '/Game/Monsters/MantisM27/RunV4/Animations'
BP = '/Game/Monsters/MantisM27/BP_MantisM27'
L = u.EditorAssetLibrary
manifest = json.loads((SOURCE / 'motion_manifest.json').read_text(encoding='utf-8'))
report = {'revision': 'RunV4', 'animation_saved': False, 'blueprint_connected': False,
          'tested': False, 'runtime_tested': False, 'rendered': False}

def receipt():
    (ROOT / 'ue_run_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End current PIE before M27 animation import/save; keep editor open')
        if BP in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
            raise RuntimeError('Preserve unsaved changes to the M27 Blueprint')
    mesh = u.load_asset('/Game/Monsters/MantisM27/BindingV2/SK_MantisM27_BindingV2')
    bp = u.load_asset(BP)
    defaults = u.get_default_object(bp.generated_class())
    if defaults.get_editor_property('visual_mesh') != mesh:
        raise RuntimeError('M27 binding changed during authoring; preserve the current Blueprint')
    report['previous'] = {}
    for prop in ['walk_clip', 'walk_speed', 'source_move_speed', 'cloak_move_speed',
                 'left_slash_clip', 'right_slash_clip', 'cloak_material']:
        value = defaults.get_editor_property(prop)
        report['previous'][prop] = value.get_path_name() if isinstance(value, u.Object) else value
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_as_skeletal = True
    options.import_animations = True
    options.import_materials = options.import_textures = False
    options.skeleton = mesh.skeleton
    data = options.anim_sequence_import_data
    data.set_editor_property('convert_scene', True)
    data.set_editor_property('convert_scene_unit', True)
    data.set_editor_property('import_uniform_scale', 1.)
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', 60)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    name = Path(manifest['file']).stem
    task = u.AssetImportTask()
    task.filename, task.destination_path, task.destination_name = str(SOURCE / manifest['file']), DEST, name
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options, task.factory = options, u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(DEST + '/' + name)
    if not clip or not task.imported_object_paths:
        raise RuntimeError('Run animation import did not produce its asset')
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', False)
    L.set_metadata_tag(clip, 'SourceAnimation', manifest['source'])
    L.set_metadata_tag(clip, 'M27.MotionRevision', 'RunV4: crouched forward hunt; original BindingV2 weights; native Khaimera/Mutant3 retarget')
    if not L.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save M27 run animation')
    report.update(animation_saved=True, animation=clip.get_path_name())
    receipt()
    # WalkClip is the shared locomotion slot used by M27's Chase state. The
    # existing tree enters it on encounter/pursuit/retreat/return, never from idle.
    defaults.set_editor_property('walk_clip', clip)
    defaults.set_editor_property('walk_speed', manifest['run_speed_cm_s'])
    defaults.set_editor_property('source_move_speed', manifest['source_speed_cm_s'])
    defaults.set_editor_property('cloak_move_speed', manifest['cloak_speed_cm_s'])
    L.set_metadata_tag(bp, 'LocomotionRevision', 'RunV4: post-encounter hunched running, including cloak retreat; existing idle/attacks/skill preserved')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    if not L.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save M27 Blueprint')
    report.update(blueprint_connected=True, blueprint=BP, speed_cm_s=manifest['run_speed_cm_s'],
                  source_speed_cm_s=manifest['source_speed_cm_s'], cloak_speed_cm_s=manifest['cloak_speed_cm_s'],
                  f6_entry='MantisM27', native_code_changed=False)
    receipt()
    u.log('M27_RUN_V4_CONNECTED_AND_SAVED ' + json.dumps(report))
except Exception as error:
    report['error'] = str(error)
    receipt()
    raise
