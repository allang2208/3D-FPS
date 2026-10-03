"""Save only the two reversed wrist rotations into the existing three pounce clips."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).parent
PROJECT = Path(u.Paths.project_dir()).resolve()
DEST = '/Game/Monsters/Mutant3Meshy/KhaimeraV2'
WORKING = DEST + '/Authoring/PounceForwardFlipV3_20261002'
LIB = u.EditorAssetLibrary
CONTRACT = json.loads((ROOT / 'animation_contract.json').read_text(encoding='utf-8'))
ROLES = list(CONTRACT['clips'])
TARGETS = {role: DEST + '/Animations/A_Mutant3_' + role for role in ROLES}
STATE = {'revision': CONTRACT['revision'], 'state': 'preparing', 'saved': [],
         'runtime_tested': False, 'visual_tested': False,
         'scope': 'All three clips: LeftHand and RightHand rotations only; reverse palm and finger direction before takeoff'}

def record():
    (ROOT / 'install_state.json').write_text(json.dumps(STATE, indent=2), encoding='utf-8')

def read_tracks(asset, names):
    model = asset.get_editor_property('data_model_interface')
    # UE 5.8's AnimationSequencerDataModel returns an empty array from the
    # deprecated GetBoneAnimationTracks. Read its actual raw poses at exact
    # source frames, with retargeting/root extraction disabled. Materialize
    # plain values before any controller mutation invalidates engine views.
    count = model.get_number_of_keys()
    available = [str(name) for name in model.get_bone_track_names()]
    available_folded = {name.casefold() for name in available}
    missing = {name for name in names if name.casefold() not in available_folded}
    if missing:
        raise RuntimeError('Required hand tracks absent in ' + asset.get_path_name() + ': ' + str(missing)
                           + '; model=' + model.get_class().get_name() + '; keys=' + str(count)
                           + '; available=' + str(available))
    options = u.AnimPoseEvaluationOptions()
    options.evaluation_type = u.AnimDataEvalType.RAW
    options.should_retarget = False
    options.extract_root_motion = False
    options.evaluate_curves = False
    result = {name: {'p': [], 'q': [], 's': []} for name in names}
    for frame in range(count):
        pose = u.AnimPoseExtensions.get_anim_pose_at_frame(asset, frame, options)
        for name in names:
            key = u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)
            result[name]['p'].append([key.translation.x, key.translation.y, key.translation.z])
            result[name]['q'].append([key.rotation.x, key.rotation.y, key.rotation.z, key.rotation.w])
            result[name]['s'].append([key.scale3d.x, key.scale3d.y, key.scale3d.z])
    return result

def expand(keys, count, default=None):
    if not keys and default is not None:
        return [default] * count
    if len(keys) == 1:
        return keys * count
    if len(keys) != count:
        raise RuntimeError('Animation key count does not match the existing clip')
    return keys

def install():
    record()
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('End existing PIE before changing or saving the production animation packages')
    dirty = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if set(TARGETS.values()) & dirty:
        raise RuntimeError('A pounce target contains unsaved changes; left untouched')
    targets = {}
    old = {}
    for role, path in TARGETS.items():
        relative = Path(path.removeprefix('/Game/'))
        disk = PROJECT / 'Content' / relative.with_suffix('.uasset')
        if hashlib.sha256(disk.read_bytes()).hexdigest() != CONTRACT['source_sha256'][role]:
            raise RuntimeError('Pounce target changed during authoring: ' + path)
        target = u.load_asset(path)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Pounce animation missing: ' + path)
        targets[role] = target
        old[role] = read_tracks(target, CONTRACT['changed_rotation_tracks'][role])
        for suffix in ('.uasset', '.uexp', '.ubulk'):
            file = PROJECT / 'Content' / relative.with_suffix(suffix)
            backup = ROOT / 'before_content' / relative.with_suffix(suffix)
            if file.exists() and not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, backup)
    skeleton = u.load_asset(DEST + '/SK_Mutant3_Claw_Skeleton')
    if not skeleton:
        raise RuntimeError('Production claw skeleton missing')
    flag = 'Interchange.FeatureFlags.Import.FBX'
    previous = u.SystemLibrary.get_console_variable_int_value(flag)
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    try:
        new = {}
        for role in ROLES:
            name = 'A_Mutant3_' + role
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh = False
            options.import_as_skeletal = True
            options.import_animations = True
            options.import_materials = False
            options.import_textures = False
            options.skeleton = skeleton
            data = options.anim_sequence_import_data
            data.set_editor_property('use_default_sample_rate', False)
            data.set_editor_property('custom_sample_rate', 60)
            data.set_editor_property('convert_scene_unit', True)
            data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task = u.AssetImportTask()
            task.filename = str(ROOT / 'animations' / (name + '.fbx'))
            task.destination_path = WORKING
            task.destination_name = name + '_HandsSource'
            task.options = options
            task.automated, task.save = True, False
            task.replace_existing, task.replace_existing_settings = True, True
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported = [u.load_asset(path) for path in task.imported_object_paths]
            imported = [asset for asset in imported if isinstance(asset, u.AnimSequence)]
            if len(imported) != 1:
                raise RuntimeError('Expected a single source animation for ' + role)
            source = imported[0]
            old_model = targets[role].get_editor_property('data_model_interface')
            new_model = source.get_editor_property('data_model_interface')
            old_rate, new_rate = old_model.get_frame_rate(), new_model.get_frame_rate()
            old_clock = (old_rate.numerator, old_rate.denominator, old_model.get_number_of_keys())
            new_clock = (new_rate.numerator, new_rate.denominator, new_model.get_number_of_keys())
            if old_clock != new_clock:
                raise RuntimeError('Source frame rate/length differs from production: ' + role
                                   + '; production=' + str(old_clock) + '; authored=' + str(new_clock))
            new[role] = read_tracks(source, CONTRACT['changed_rotation_tracks'][role])
        patches = {}
        for role in ROLES:
            target = targets[role]
            count = target.get_editor_property('data_model_interface').get_number_of_keys()
            patches[role] = {}
            for name in CONTRACT['changed_rotation_tracks'][role]:
                patches[role][name] = {
                    'p': expand(old[role][name]['p'], count),
                    'q': expand(new[role][name]['q'], count),
                    's': expand(old[role][name]['s'], count, [1., 1., 1.]),
                }
        (ROOT / 'production_hand_keys.json').write_text(json.dumps(patches, indent=2), encoding='utf-8')
        STATE['state'] = 'saving production hand rotation tracks'
        record()
        for role in ROLES:
            target = targets[role]
            controller = target.get_editor_property('controller')
            controller.open_bracket('Mutant3 reverse both palms and hand directions before takeoff', False)
            try:
                for name, keys in patches[role].items():
                    if not controller.set_bone_track_keys(
                            name, [u.Vector(*key) for key in keys['p']],
                            [u.Quat(*key) for key in keys['q']],
                            [u.Vector(*key) for key in keys['s']], False):
                        raise RuntimeError('Could not save hand rotation track ' + role + '/' + name)
            finally:
                controller.close_bracket(False)
            LIB.set_metadata_tag(target, 'PounceHandRevision', CONTRACT['revision'])
            LIB.set_metadata_tag(target, 'PounceHandAuthorSource', str(ROOT / 'production_hand_keys.json'))
            if not LIB.save_loaded_asset(target, False):
                raise RuntimeError('Could not save production animation ' + TARGETS[role])
            STATE['saved'].append({'asset': target.get_path_name(),
                                   'rotation_tracks': len(patches[role]),
                                   'seconds': CONTRACT['clips'][role]['seconds']})
            record()
            u.log('MUTANT3_FORWARD_FLIP_SAVED ' + role)
        STATE['state'] = 'Three production pounce clips saved; testing left to the user'
        CONTRACT['state'] = STATE['state']
        (ROOT / 'animation_contract.json').write_text(json.dumps(CONTRACT, indent=2), encoding='utf-8')
        record()
        u.log('MUTANT3_FORWARD_FLIP_INSTALL_COMPLETE 3 production clips')
    finally:
        u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous))

try:
    install()
except Exception as error:
    STATE['state'] = 'installation interrupted'
    STATE['error'] = str(error)
    record()
    raise
