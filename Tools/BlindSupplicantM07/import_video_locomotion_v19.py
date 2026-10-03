"""Save two video-reference locomotion candidates and the existing M07 AI/F6 BP."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'VideoLocomotionV19'
MOVE = OUT / 'Move'
MANIFEST = MOVE / 'video_locomotion_manifest_v19.json'
REPORT = OUT / 'ue_video_locomotion_delivery_v19.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST + '/AnimationsVideoMotionV19'
BP = DEST + '/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase')
SAVE_PATHS = {BP, *(ANIM + '/A_M07_' + role for role in ROLES)}
LIB = u.EditorAssetLibrary

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT / 'FPSGAME.uproject':
    raise RuntimeError('M07 video locomotion production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; video locomotion saving needs an editing context.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
for role in ROLES:
    source = Path(manifest['clips'][role]['file']).resolve()
    if not source.is_file() or not source.is_relative_to(MOVE.resolve()):
        raise RuntimeError('Missing or out-of-scope video locomotion export: ' + str(source))

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


report = {
    'revision': 'VideoLocomotionV19', 'saved': False, 'assets': [], 'clips': {},
    'reference': {'url': 'https://www.youtube.com/watch?v=dJ-Ak3X7tiM',
                  'start_seconds': 120, 'end_seconds': 125,
                  'source_record': str(OUT / 'Reference/source.json')},
    'authoring_manifest': str(MANIFEST),
    'scope': 'Two video-reference gait candidates and existing AI/F6 references only',
    'mesh': asset_path(mesh), 'skeleton': asset_path(skeleton),
    'geometry_modified': False, 'weights_modified': False,
    'reference_pose_modified': False, 'cloth_modified': False,
    'native_rebuild_required': False, 'runtime_tested': False,
    'visual_tested': False, 'tested': False, 'user_review_pending': True,
    'previous_references': {prop: asset_path(defaults.get_editor_property(prop))
                            for prop in ('slow_walk_clip', 'chase_clip', 'walk_clip')},
    'previous_source_speeds': {prop: defaults.get_editor_property(prop)
                              for prop in ('source_walk_speed', 'source_chase_speed')},
    'retained_gameplay_speeds': {prop: defaults.get_editor_property(prop)
                                for prop in ('walk_speed', 'chase_speed')},
    'retained_action_references': {prop: asset_path(defaults.get_editor_property(prop))
                                   for prop in ('idle_clip', 'death_clip',
                                                'magic_gather_clip', 'magic_release_clip',
                                                'wall_listen_clip')},
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save(asset):
    path = asset_path(asset)
    if not path or path.split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('Video locomotion save outside the two clips and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Video locomotion package could not save: ' + path)
    if path not in report['assets']:
        report['assets'].append(path)
    receipt()


receipt()
clips = {}
for role in ROLES:
    entry = manifest['clips'][role]
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
        raise RuntimeError('Video locomotion import did not preserve the original skeleton: ' + role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'LocomotionRevision', 'M07 V19: video reference 120-125s; adapted candidate, user review pending')
    save(clip)
    clips[role] = clip
    report['clips'][role] = {'asset': asset_path(clip), 'source_fbx': entry['file'],
                             'duration_s': clip.get_play_length(),
                             'source_speed_cm_s': entry['speed_cm_s']}

defaults.set_editor_property('slow_walk_clip', clips['SlowWalk'])
defaults.set_editor_property('chase_clip', clips['Chase'])
defaults.set_editor_property('walk_clip', clips['Chase'])
defaults.set_editor_property('source_walk_speed', float(manifest['clips']['SlowWalk']['speed_cm_s']))
defaults.set_editor_property('source_chase_speed', float(manifest['clips']['Chase']['speed_cm_s']))
LIB.set_metadata_tag(blueprint, 'LocomotionRevision', 'VideoLocomotionV19: existing original body, cloth and AI/F6 retained')
save(blueprint)
report.update(saved=True, blueprint=asset_path(blueprint),
              stage='Two video-reference gait assets and existing AI/F6 Blueprint actually saved')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT),
                runtime_tested=False, tested=False, user_review_pending=True)
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT / filename
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding='utf-8-sig'))
        record.update(locomotion_revision='VideoLocomotionV19',
                      locomotion_delivery=str(REPORT),
                      locomotion_assets={role: asset_path(clip) for role, clip in clips.items()},
                      runtime_tested=False, tested=False, user_review_pending=True)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V19_VIDEO_REFERENCE_LOCOMOTION_SAVED ' + str(REPORT), flush=True)
