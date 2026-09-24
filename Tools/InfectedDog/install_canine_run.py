"""Import one authored canine run and bind its three locomotion slots.

Called by the specific Fit/Natural installers with explicit source and destination.
No mesh import, skeleton edits, gameplay changes, previews or unrelated saves.
"""
import json
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from meshy_animation_units import match_bind_root_scale

PROJECT = Path('D:/FPS3D/FPSGAME')
SLOTS = ('Run', 'RunTurnLeft', 'RunTurnRight')


def main(*, ROOT, DEST, NAME, REVISION):
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor is not None and editor.get_game_world() is not None:
        raise RuntimeError('End the current play session before saving the canine run')
    before = json.loads((ROOT / 'binding_before.json').read_text(encoding='utf-8'))
    authored = json.loads((ROOT / 'authoring.json').read_text(encoding='utf-8'))
    bp = u.load_asset(before['blueprint'])
    cdo = u.get_default_object(bp.generated_class())
    dataset = cdo.get_editor_property('animation_set')
    mesh = dataset.get_editor_property('reference_mesh')
    if dataset.get_path_name() != before['dataset'] or mesh.get_path_name() != before['mesh']:
        raise RuntimeError('The active infected-dog mesh or animation set has changed')
    skeleton = mesh.get_editor_property('skeleton')
    dirty = {p.get_name().casefold() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    affected = {a.get_path_name().split('.')[0].casefold() for a in (bp, dataset, mesh, skeleton)}
    if affected & dirty or any(p.startswith(DEST.casefold() + '/') for p in dirty):
        raise RuntimeError('Preserving unsaved edits to the target infected-dog assets')
    actions = dataset.get_editor_property('actions')
    clip_path = DEST + '/' + NAME + '.' + NAME
    lib = u.EditorAssetLibrary
    completed_baseline = lib.get_metadata_tag(dataset, 'InfectedDog.MeshyRevision') == 'MeshyCanineMouthMotionV2-20260924'
    previous = {}
    for role in SLOTS:
        current = actions[role].get_editor_property('sequence').get_path_name()
        baseline_name = 'A_InfectedDogMeshy_' + role
        baseline_path = '/Game/Monsters/InfectedDog/MeshyV2/Animations/' + baseline_name + '.' + baseline_name
        # Full body/action rebuild restores these known clips. A historical
        # before-snapshot must not prevent reapplying the accepted run afterwards.
        from_completed = completed_baseline and current == baseline_path
        if current not in (before['actions'][role]['sequence'], clip_path) and not from_completed:
            raise RuntimeError('The run binding changed during authoring: ' + role)
        previous[role] = current
    if lib.does_asset_exist(clip_path):
        existing = u.load_asset(clip_path)
        if lib.get_metadata_tag(existing, 'InfectedDog.RunRevision') != REVISION:
            raise RuntimeError('Preserving an independently created run asset')
    report = {'state': 'importing', 'source': authored['source'],
              'source_commit': authored['source_commit'], 'license': authored['license'],
              'animation_set': dataset.get_path_name(), 'previous_sequences': previous,
              'previous_run_speed': dataset.get_editor_property('run_speed'), 'saved': [],
              'runtime_tested': False, 'preview_rendered': False,
              'mesh_or_weights_changed': False, 'gameplay_changed': False}

    def record():
        (ROOT / 'installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    def save(asset):
        if not lib.save_loaded_asset(asset, False):
            raise RuntimeError('Could not save ' + asset.get_path_name())
        report['saved'].append(asset.get_path_name())
        record()

    record()
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    data = options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate', False)
    sample_rate = int(authored.get('fps', 60))
    data.set_editor_property('custom_sample_rate', sample_rate)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('remove_redundant_keys', False)
    task = u.AssetImportTask()
    task.filename = authored['fbx']
    task.destination_name = NAME
    task.destination_path = DEST
    task.options = options
    task.automated = True
    task.save = False
    task.replace_existing = True
    cvar = 'Interchange.FeatureFlags.Import.FBX'
    previous_cvar = u.SystemLibrary.get_console_variable_int_value(cvar)
    u.SystemLibrary.execute_console_command(None, cvar + ' 0')
    try:
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    finally:
        u.SystemLibrary.execute_console_command(None, cvar + ' ' + str(previous_cvar))
    imported = [u.load_asset(path) for path in task.imported_object_paths]
    clip = next((asset for asset in imported if isinstance(asset, u.AnimSequence)), None)
    if clip is None:
        raise RuntimeError('Canine run FBX import did not produce an animation')
    lib.set_metadata_tag(clip, 'InfectedDog.RunRevision', REVISION)
    lib.set_metadata_tag(clip, 'InfectedDog.AnimationSource', authored['source_url'])
    lib.set_metadata_tag(clip, 'InfectedDog.AnimationLicense', authored['license'])
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.ANIM_FIRST_FRAME)
    clip.set_editor_property('rate_scale', 1.)
    clip.get_editor_property('platform_target_frame_rate').set_editor_property('default', u.FrameRate(sample_rate, 1))
    clip.set_preview_skeletal_mesh(mesh)
    report['root_units'] = match_bind_root_scale(clip, mesh)
    save(clip)
    # Retain each action's transition, playback and combat contract verbatim.
    for role in SLOTS:
        action = actions[role]
        action.set_editor_property('sequence', clip)
        actions[role] = action
    dataset.set_editor_property('actions', actions)
    dataset.set_editor_property('run_speed', authored['reference_run_speed_cm_s'])
    lib.set_metadata_tag(dataset, 'InfectedDog.RunRevision', REVISION)
    save(dataset)
    report.update(state='assets_saved_and_run_bound', sequence=clip.get_path_name(),
                  slots=list(SLOTS), run_speed=authored['reference_run_speed_cm_s'],
                  actor_movement_speed_changed=False,
                  turn_policy=authored['turn_policy'])
    record()
    print('INFECTED_DOG_RUN_SAVED ' + json.dumps(report, ensure_ascii=False))
    return report
