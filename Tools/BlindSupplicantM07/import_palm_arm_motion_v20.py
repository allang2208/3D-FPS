"""Save M07 palm/arm actions into the existing original rig and AI/F6 Blueprint."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'PalmArmMotionV20'
MANIFEST = OUT / 'Motion/palm_arm_motion_manifest_v20.json'
REPORT = OUT / 'ue_palm_arm_delivery_v20.json'
NATIVE = OUT / 'native_magic_delivery_v20.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST + '/AnimationsPalmArmV20'
BP = DEST + '/BP_BlindSupplicantM07'
LIB = u.EditorAssetLibrary

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT / 'FPSGAME.uproject':
    raise RuntimeError('M07 palm/arm production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; palm/arm saving needs an editing context.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
native_delivery = json.loads(NATIVE.read_text(encoding='utf-8-sig'))
if not native_delivery.get('game_built') or not native_delivery.get('editor_built'):
    raise RuntimeError('M07 V20 magic native targets must finish production before final action integration.')
entries = manifest['clips']
roles = ('SlowWalk', 'Chase', 'SweepLeft', 'SweepRight') + (('Idle',) if 'Idle' in entries else ())
save_paths = {BP, *(ANIM + '/A_M07_' + role for role in roles)}
for role in roles:
    source = Path(entries[role]['file']).resolve()
    if not source.is_file() or not source.is_relative_to(OUT.resolve()):
        raise RuntimeError('Missing or out-of-scope palm/arm export: ' + str(source))

skeleton = u.load_asset(DEST + '/SK_M07_ReferenceOriginalV11')
blueprint = u.load_asset(BP)
if not skeleton or not blueprint:
    raise RuntimeError('Existing original M07 skeleton and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(blueprint)
defaults = u.get_default_object(blueprint.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
if not mesh or mesh.get_editor_property('skeleton') != skeleton:
    raise RuntimeError('Existing M07 display must retain the original reference skeleton.')


def asset_path(asset):
    return asset.get_path_name() if asset else None


properties = {'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase', 'walk_clip': 'Chase',
              'melee_left_clip': 'SweepLeft', 'melee_right_clip': 'SweepRight', 'attack_clip': 'SweepLeft'}
if 'Idle' in entries:
    properties['idle_clip'] = 'Idle'
report = {
    'revision': 'PalmArmMotionV20', 'saved': False, 'assets': [], 'clips': {},
    'authoring_manifest': str(MANIFEST), 'mesh': asset_path(mesh), 'skeleton': asset_path(skeleton),
    'scope': 'Palm/arm animation candidates and existing original AI/F6 Blueprint',
    'geometry_modified': False, 'weights_modified': False, 'reference_pose_modified': False,
    'cloth_modified': False, 'native_rebuild_required': True, 'native_built': True,
    'native_delivery': str(NATIVE), 'magic_prediction_revision': 'ReleaseContactInterceptV20',
    'runtime_tested': False, 'visual_tested': False, 'tested': False, 'user_review_pending': True,
    'previous_references': {prop: asset_path(defaults.get_editor_property(prop)) for prop in properties},
    'retained_gameplay_speeds': {prop: defaults.get_editor_property(prop) for prop in ('walk_speed', 'chase_speed')},
    'retained_action_references': {prop: asset_path(defaults.get_editor_property(prop)) for prop in (
        'death_clip', 'magic_gather_clip', 'magic_release_clip', 'wall_listen_clip')},
    'retained_melee_clock': {prop: defaults.get_editor_property(prop) for prop in (
        'left_contact_time', 'right_contact_time', 'contact_window_seconds', 'melee_playback_rate')},
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save(asset):
    path = asset_path(asset)
    if not path or path.split('.', 1)[0] not in save_paths:
        raise RuntimeError('Palm/arm save outside the action candidates and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Palm/arm package could not save: ' + path)
    if path not in report['assets']:
        report['assets'].append(path)
    receipt()


receipt()
clips = {}
for role in roles:
    entry = entries[role]
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = options.import_textures = options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.anim_sequence_import_data
    data.convert_scene = data.convert_scene_unit = True
    data.import_uniform_scale = 1.
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', int(entry.get('fps', manifest.get('fps', 30))))
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    task = u.AssetImportTask()
    task.filename = entry['file']
    task.destination_name = 'A_M07_' + role
    task.destination_path = ANIM
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(ANIM + '/A_M07_' + role)
    if not clip or not task.imported_object_paths or clip.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('Palm/arm import did not preserve the original skeleton: ' + role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'PalmArmRevision', 'M07 V20: rear-facing travel palms and anatomical arm/sweep recovery')
    save(clip)
    clips[role] = clip
    report['clips'][role] = {'asset': asset_path(clip), 'source_fbx': entry['file'],
                            'duration_s': clip.get_play_length(), 'authoring': entry}

for prop, role in properties.items():
    defaults.set_editor_property(prop, clips[role])
for prop, role in (('source_walk_speed', 'SlowWalk'), ('source_chase_speed', 'Chase')):
    if 'speed_cm_s' in entries[role]:
        defaults.set_editor_property(prop, float(entries[role]['speed_cm_s']))
LIB.set_metadata_tag(blueprint, 'PalmArmRevision', 'PalmArmMotionV20: existing original body, cloth and AI/F6 retained')
save(blueprint)
report.update(saved=True, blueprint=asset_path(blueprint),
              stage='Palm/arm action assets and existing AI/F6 Blueprint actually saved')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT),
                runtime_tested=False, tested=False, user_review_pending=True)
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT / filename
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding='utf-8-sig'))
        record.update(palm_arm_revision='PalmArmMotionV20', palm_arm_delivery=str(REPORT),
                      palm_arm_assets={role: asset_path(clip) for role, clip in clips.items()},
                      locomotion_revision='PalmArmMotionV20', locomotion_delivery=str(REPORT),
                      locomotion_assets={role: asset_path(clips[role]) for role in ('SlowWalk', 'Chase')},
                      melee_animation_revision='PalmArmMotionV20',
                      magic_prediction_revision='ReleaseContactInterceptV20',
                      magic_prediction_native_delivery=str(NATIVE),
                      runtime_tested=False, tested=False, user_review_pending=True)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V20_PALM_ARM_ACTIONS_SAVED ' + str(REPORT), flush=True)
