"""Save two authored M07 casting clips and wire the existing AI/F6 Blueprint."""
import json
from pathlib import Path
import shutil

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'FlowCastV24'
MOTION = OUT/'Motion'
MANIFEST = MOTION/'flow_cast_manifest_v24.json'
REPORT = OUT/'ue_flow_cast_delivery_v24.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsFlowCastV24'
BP = DEST+'/BP_BlindSupplicantM07'
ROLES = ('MagicGather', 'MagicRelease')
PROPS = {'magic_gather_clip': 'MagicGather', 'magic_release_clip': 'MagicRelease'}
LIB = u.EditorAssetLibrary
SAVE_PATHS = {BP, *(ANIM+'/A_M07_'+role for role in ROLES)}

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 casting belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor or editor.is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; casting import needs an editing context.')

manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
for role in ROLES:
    source = Path(manifest['clips'][role]['file']).resolve()
    if not source.is_file() or not source.is_relative_to(MOTION.resolve()):
        raise RuntimeError('Missing or out-of-scope casting export: '+str(source))

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
    raise RuntimeError('Original M07 display mesh/reference must be retained.')


def path(asset):
    return asset.get_path_name() if asset else None


report = dict(revision='FlowCastV24', saved=False, assets=[], clips={}, authoring_manifest=str(MANIFEST),
    mesh=path(mesh), skeleton=path(skeleton), before_blueprint=str(backup),
    scope='Only MagicGather/MagicRelease, release contact and forward charge offset in existing AI/F6 BP',
    previous_references={prop: path(defaults.get_editor_property(prop)) for prop in PROPS},
    previous_release_contact_seconds=defaults.get_editor_property('magic_release_contact_time'),
    previous_charge_offset_cm=defaults.get_editor_property('magic_charge_forward_offset_cm'),
    retained_action_references={prop: path(defaults.get_editor_property(prop)) for prop in (
        'idle_clip', 'walk_clip', 'slow_walk_clip', 'chase_clip', 'melee_left_clip', 'melee_right_clip', 'death_clip', 'wall_listen_clip')},
    retained_speed_values={prop: defaults.get_editor_property(prop) for prop in (
        'source_walk_speed', 'source_chase_speed', 'walk_speed', 'chase_speed')},
    geometry_modified=False, weights_modified=False, reference_pose_modified=False, cloth_modified=False,
    tested=False, runtime_tested=False, visual_tested=False, user_review_pending=True)


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def save(asset):
    name = path(asset)
    if name.split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('Casting save outside its two clips and existing BP.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Casting package could not save: '+name)
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
        raise RuntimeError('Casting import did not retain original skeleton: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'CastingRevision', 'M07 V24: weight, shoulder, elbow, wrist and digit sequencing')
    save(clip)
    clips[role] = clip
    report['clips'][role] = dict(asset=path(clip), source_fbx=entry['file'], duration_s=clip.get_play_length())

for prop, role in PROPS.items():
    defaults.set_editor_property(prop, clips[role])
defaults.set_editor_property('magic_release_contact_time', manifest['release_contact_seconds'])
defaults.set_editor_property('magic_charge_forward_offset_cm', manifest['charge_forward_offset_cm'])
LIB.set_metadata_tag(blueprint, 'CastingRevision', 'FlowCastV24: linked whole-body cast, forward fire/ice charge and shared release origin')
save(blueprint)
report.update(saved=True, blueprint=path(blueprint),
    release_contact_seconds=defaults.get_editor_property('magic_release_contact_time'),
    charge_forward_offset_cm=defaults.get_editor_property('magic_charge_forward_offset_cm'),
    stage='Two casting animations and actual AI/F6 Blueprint imported and saved')
receipt()
manifest.update(ue_imported=True, ue_saved=True, ue_save_receipt=str(REPORT))
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(casting_revision='FlowCastV24', casting_delivery=str(REPORT),
        casting_assets={role: path(clip) for role, clip in clips.items()},
        casting_release_contact_seconds=report['release_contact_seconds'],
        casting_charge_forward_offset_cm=report['charge_forward_offset_cm'],
        tested=False, runtime_tested=False, user_review_pending=True)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('M07_V24_FLOW_CAST_SAVED '+str(REPORT), flush=True)
