"""Save M07 V25 gait clearance and two authored sweeps into the existing AI/F6 BP."""
import json
from pathlib import Path
import shutil

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'ClearanceSweepV25'
MOTION = OUT/'Motion'
MANIFEST = MOTION/'clearance_sweep_manifest_v25.json'
REPORT = OUT/'ue_clearance_sweep_delivery_v25.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsClearanceSweepV25'
BP = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase', 'SweepLeft', 'SweepRight')
PROPS = {'slow_walk_clip': 'SlowWalk', 'walk_clip': 'Chase', 'chase_clip': 'Chase',
         'melee_left_clip': 'SweepLeft', 'melee_right_clip': 'SweepRight', 'attack_clip': 'SweepLeft'}
LIB = u.EditorAssetLibrary
SAVE_PATHS = {BP, *(ANIM+'/A_M07_'+role for role in ROLES)}

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V25 belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('M07_V25_PIE_PRESERVED: finish the current play session before importing/saving this Blueprint.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
for role in ROLES:
    source = Path(manifest['clips'][role]['file']).resolve()
    if not source.is_file() or not source.is_relative_to(MOTION.resolve()):
        raise RuntimeError('Missing or out-of-scope V25 export: '+str(source))

backup = OUT/'Before/BP_BlindSupplicantM07.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(PROJECT/'Content/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07.uasset', backup)
skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
blueprint = u.load_asset(BP)
u.BlueprintEditorLibrary.compile_blueprint(blueprint)
defaults = u.get_default_object(blueprint.generated_class())
mesh = defaults.get_editor_property('visual_mesh')
if not mesh or mesh.get_editor_property('skeleton') != skeleton:
    raise RuntimeError('The original M07 display/reference must be retained.')


def path(asset):
    return asset.get_path_name() if asset else None


settings = {'left_contact_time': manifest['clips']['SweepLeft']['contact_seconds'],
    'right_contact_time': manifest['clips']['SweepRight']['contact_seconds'],
    'contact_window_seconds': manifest['contact_window_seconds'],
    'melee_playback_rate': manifest['melee_playback_rate'],
    'gill_clearance_angle_degrees': manifest['gill_runtime_max_opening_degrees'],
    'enable_gill_bone_clearance': True}
report = dict(revision='ClearanceSweepV25', saved=False, assets=[], clips={}, authoring_manifest=str(MANIFEST),
    mesh=path(mesh), skeleton=path(skeleton), before_blueprint=str(backup),
    scope='Four clips, existing AI/F6 references, shared melee timing and bounded gill clearance settings',
    previous_references={prop: path(defaults.get_editor_property(prop)) for prop in PROPS},
    previous_settings={prop: defaults.get_editor_property(prop) for prop in settings},
    retained_action_references={prop: path(defaults.get_editor_property(prop)) for prop in (
        'idle_clip', 'magic_gather_clip', 'magic_release_clip', 'death_clip', 'wall_listen_clip')},
    retained_speed_values={prop: defaults.get_editor_property(prop) for prop in (
        'source_walk_speed', 'source_chase_speed', 'walk_speed', 'chase_speed')},
    geometry_modified=False, weights_modified=False, reference_pose_modified=False, cloth_modified=False,
    tested=False, runtime_tested=False, visual_tested=False, performance_measured=False, user_review_pending=True)


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def save(asset):
    name = path(asset)
    if name.split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('V25 save outside its four clips and existing BP.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('V25 package could not save: '+name)
    if name not in report['assets']:
        report['assets'].append(name)
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
    data.set_editor_property('custom_sample_rate', manifest['fps'])
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    task = u.AssetImportTask()
    task.filename = entry['file']
    task.destination_name = 'A_M07_'+role
    task.destination_path = ANIM
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(ANIM+'/A_M07_'+role)
    if not clip or not task.imported_object_paths or clip.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('V25 import did not retain the original skeleton: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'MotionRevision', 'M07 V25: anterior gait corridor, baked leaf clearance and body-led sweep')
    save(clip)
    clips[role] = clip
    report['clips'][role] = dict(asset=path(clip), source_fbx=entry['file'], duration_s=clip.get_play_length())

for prop, role in PROPS.items():
    defaults.set_editor_property(prop, clips[role])
for prop, value in settings.items():
    defaults.set_editor_property(prop, value)
LIB.set_metadata_tag(blueprint, 'MotionRevision', 'ClearanceSweepV25: gait arm corridor, leaf surface clearance and authored whole-body sweeps')
save(blueprint)
report.update(saved=True, blueprint=path(blueprint), settings=settings,
    stage='Four V25 animations and actual AI/F6 Blueprint imported and saved; native build recorded separately')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(locomotion_revision='ClearanceSweepV25', locomotion_delivery=str(REPORT),
        locomotion_assets={role: path(clips[role]) for role in ('SlowWalk', 'Chase')},
        melee_revision='ClearanceSweepV25', melee_delivery=str(REPORT),
        melee_assets={role: path(clips[role]) for role in ('SweepLeft', 'SweepRight')},
        gill_clearance_revision='SurfacePatchesV25',
        tested=False, runtime_tested=False, performance_measured=False, user_review_pending=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('M07_V25_CLEARANCE_SWEEP_SAVED '+str(REPORT), flush=True)
