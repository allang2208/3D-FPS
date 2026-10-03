"""Import two complete reference-posture M07 gaits into the existing AI/F6 BP."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'FullReferenceGaitV21'
MOTION = OUT / 'Motion'
MANIFEST = MOTION / 'full_reference_gait_manifest_v21.json'
REPORT = OUT / 'ue_full_reference_gait_delivery_v21.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST + '/AnimationsFullReferenceV21'
BP = DEST + '/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase')
LIB = u.EditorAssetLibrary
SAVE_PATHS = {BP, *(ANIM + '/A_M07_' + role for role in ROLES)}

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT / 'FPSGAME.uproject':
    raise RuntimeError('M07 full reference gait belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; reference gait saving needs an editing context.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
for role in ROLES:
    source = Path(manifest['clips'][role]['file']).resolve()
    if not source.is_file() or not source.is_relative_to(MOTION.resolve()):
        raise RuntimeError('Missing or out-of-scope full reference gait export: ' + str(source))

skeleton = u.load_asset(DEST + '/SK_M07_ReferenceOriginalV11')
blueprint = u.load_asset(BP)
if not skeleton or not blueprint:
    raise RuntimeError('Original M07 skeleton and existing AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(blueprint)
defaults = u.get_default_object(blueprint.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
if not mesh or mesh.get_editor_property('skeleton') != skeleton:
    raise RuntimeError('M07 original display/reference must be retained.')


def path(asset):
    return asset.get_path_name() if asset else None


props = {'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase', 'walk_clip': 'Chase'}
speed_props = ('source_walk_speed', 'source_chase_speed', 'walk_speed', 'chase_speed')
report = {
    'revision': 'FullReferenceGaitV21', 'saved': False, 'assets': [], 'clips': {},
    'authoring_manifest': str(MANIFEST), 'mesh': path(mesh), 'skeleton': path(skeleton),
    'scope': 'Two complete locomotion clips and their existing AI/F6 speed/animation references',
    'geometry_modified': False, 'weights_modified': False, 'reference_pose_modified': False,
    'cloth_modified': False, 'native_rebuild_required': False,
    'runtime_tested': False, 'visual_tested': False, 'tested': False, 'user_review_pending': True,
    'previous_references': {prop: path(defaults.get_editor_property(prop)) for prop in props},
    'previous_speed_values': {prop: defaults.get_editor_property(prop) for prop in speed_props},
    'retained_action_references': {prop: path(defaults.get_editor_property(prop)) for prop in (
        'idle_clip', 'melee_left_clip', 'melee_right_clip', 'death_clip',
        'magic_gather_clip', 'magic_release_clip', 'wall_listen_clip')},
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def save(asset):
    asset_name = path(asset)
    if not asset_name or asset_name.split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('Full reference gait save outside two clips and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Full reference gait package could not save: ' + asset_name)
    if asset_name not in report['assets']:
        report['assets'].append(asset_name)
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
        raise RuntimeError('Full reference gait import did not preserve original skeleton: ' + role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'LocomotionRevision', 'M07 V21: fullbody posture and reference-cycle choreography')
    save(clip)
    clips[role] = clip
    report['clips'][role] = {'asset': path(clip), 'source_fbx': entry['file'],
                            'duration_s': clip.get_play_length(), 'authoring': entry}

for prop, role in props.items():
    defaults.set_editor_property(prop, clips[role])
for source_prop, gameplay_prop, role in (
    ('source_walk_speed', 'walk_speed', 'SlowWalk'), ('source_chase_speed', 'chase_speed', 'Chase')):
    entry = manifest['clips'][role]
    source_speed = float(entry.get('source_speed_cm_s', entry['speed_cm_s']))
    defaults.set_editor_property(source_prop, source_speed)
    if 'ai_speed_cm_s' in entry:
        defaults.set_editor_property(gameplay_prop, float(entry['ai_speed_cm_s']))
LIB.set_metadata_tag(blueprint, 'LocomotionRevision', 'FullReferenceGaitV21: original body, V20 attack/magic, existing AI/F6 retained')
save(blueprint)
report.update(saved=True, blueprint=path(blueprint),
              speed_values={prop: defaults.get_editor_property(prop) for prop in speed_props},
              stage='Two full reference gait assets and existing AI/F6 Blueprint actually saved')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT),
                runtime_tested=False, tested=False, user_review_pending=True)
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT / filename
    if record_path.is_file():
        record = json.loads(record_path.read_text(encoding='utf-8-sig'))
        record.update(locomotion_revision='FullReferenceGaitV21', locomotion_delivery=str(REPORT),
                      locomotion_assets={role: path(clip) for role, clip in clips.items()},
                      locomotion_speed_values=report['speed_values'],
                      runtime_tested=False, tested=False, user_review_pending=True)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V21_FULL_REFERENCE_GAITS_SAVED ' + str(REPORT), flush=True)
