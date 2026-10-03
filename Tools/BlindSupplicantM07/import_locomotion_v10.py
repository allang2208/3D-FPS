"""Save the two V10 M-07 gait clips into the existing AI/F6 character.

This production entry imports animation only, on the saved OriginalV08
reference skeleton. OriginalV09 display/cloth/material/physics packages,
other actions, movement speeds, combat contacts and navigation are retained.
It never starts PIE, previews an action or runs an acceptance test.
"""
import json
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
SOURCE = ROOT/'LocomotionV10'
MANIFEST = SOURCE/'locomotion_manifest_v10.json'
REPORT = SOURCE/'ue_locomotion_delivery_v10.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM_DEST = DEST+'/AnimationsLocomotionV10'
SKELETON_PATH = DEST+'/SK_M07_ReferenceOriginalV08'
DISPLAY_PATH = DEST+'/SK_M07_OriginalV09'
BP_PATH = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase')
CLIP_PROPERTIES = {'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase',
                   'walk_clip': 'Chase'}
SAVE_PATHS = {BP_PATH, *(ANIM_DEST+'/A_M07_'+role for role in ROLES)}
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V10 locomotion production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving the M07 locomotion candidate.')

report = {
    'revision': 'locomotion_v10',
    'scope': 'SlowWalk and Chase larger human stride, arm swing and hand animation only',
    'saved': False,
    'assets': [],
    'tested': False,
    'runtime_tested': False,
    'visual_tested': False,
    'user_accepted_motion': False,
    'user_review_pending': True,
    'reference_skeleton_reused': SKELETON_PATH,
    'preview_display_reused': DISPLAY_PATH,
    'reference_pose_update_requested': False,
    'meshes_imported': False,
    'cloth_modified': False,
    'materials_modified': False,
    'physics_modified': False,
    'navigation_modified': False,
    'movement_speeds_modified': False,
    'combat_timing_modified': False,
    'other_actions_reimported': False,
    'changed_cdo_properties': {},
    'motion_source': str(MANIFEST),
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def asset_path(asset):
    return asset.get_path_name() if asset else None


def save(asset):
    # The reused skeleton/display and all other packages are outside V10 scope.
    if asset is None or asset.get_path_name().split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V10 locomotion cannot save an asset outside its two clips and character Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V10 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()


def animation_options(skeleton, fps):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    # These remain explicit even though this is animation-only import.
    options.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose', False)
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose', False)
    data = options.anim_sequence_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', int(fps))
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    return options


def motion_inputs():
    if not MANIFEST.is_file():
        raise RuntimeError('Complete the V10 locomotion_manifest_v10.json export before UE import.')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    files = {}
    for role in ROLES:
        clip = manifest.get('clips', {}).get(role, {})
        filename = Path(clip['file']) if clip.get('file') else SOURCE/'rig_motion'/('A_M07_'+role+'.fbx')
        if not filename.is_absolute():
            relative = filename
            filename = SOURCE/relative
            if not filename.is_file() and len(relative.parts) == 1:
                filename = SOURCE/'rig_motion'/relative
        if not filename.is_file() or not filename.resolve().is_relative_to(SOURCE.resolve()):
            raise RuntimeError('M07 V10 '+role+' export is absent or outside its locomotion production directory: '+str(filename))
        files[role] = filename
    return manifest, files


def import_clip(role, filename, skeleton, fps):
    name = 'A_M07_'+role
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = ANIM_DEST
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = animation_options(skeleton, fps)
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    clip = u.load_asset(ANIM_DEST+'/'+name)
    if clip is None or not task.imported_object_paths:
        raise RuntimeError('M07 V10 locomotion source did not import: '+str(filename))
    return clip


motion, motion_files = motion_inputs()
skeleton = u.load_asset(SKELETON_PATH)
display = u.load_asset(DISPLAY_PATH)
bp = u.load_asset(BP_PATH)
if not skeleton or not display or not bp:
    raise RuntimeError('Save the existing V08 reference skeleton, V09 display and M07 AI/F6 Blueprint before V10 animation import.')
report['stage'] = 'M07 V10 animation-only production started'
report['skeleton'] = asset_path(skeleton)
report['display_mesh'] = asset_path(display)
receipt()

clips = {}
for role in ROLES:
    clip = import_clip(role, motion_files[role], skeleton, motion.get('fps', 30))
    clip.set_preview_skeletal_mesh(display)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'M07 LocomotionV10: larger human stride, coordinated arm swing and hand animation; OriginalV08 reference; user review pending')
    LIB.set_metadata_tag(clip, 'LocomotionSourceManifest', str(MANIFEST))
    LIB.set_metadata_tag(clip, 'LocomotionContract', json.dumps(motion.get('clips', {}).get(role, {}), ensure_ascii=False))
    save(clip)
    clips[role] = clip

u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
report['preserved_settings'] = {
    prop: defaults.get_editor_property(prop)
    for prop in ('walk_speed', 'chase_speed', 'source_walk_speed', 'source_chase_speed',
                 'left_contact_time', 'right_contact_time', 'contact_time',
                 'contact_end', 'contact_window_seconds', 'animation_blend_seconds')
}
report['preserved_other_action_references'] = {
    prop: asset_path(defaults.get_editor_property(prop))
    for prop in ('idle_clip', 'attack_clip', 'melee_left_clip', 'melee_right_clip',
                 'death_clip', 'wall_listen_clip')
}
combat = defaults.get_editor_property('combat')
knockdown = defaults.get_editor_property('knockdown')
report['preserved_other_action_references'].update({
    'combat.'+prop: asset_path(combat.get_editor_property(prop))
    for prop in ('hit_clip', 'dizzy_clip')
})
report['preserved_other_action_references'].update({
    'knockdown.'+prop: asset_path(knockdown.get_editor_property(prop))
    for prop in ('fall_clip', 'get_up_clip', 'prone_get_up_clip')
})

# Current runtime has source speed calibration and normalized gait-phase
# transfer, but no separate cycle/contact metadata UPROPERTY. Preserve both
# speed calibrations and every combat contact; only replace these three refs.
for prop, role in CLIP_PROPERTIES.items():
    report['changed_cdo_properties'][prop] = {
        'previous': asset_path(defaults.get_editor_property(prop)),
        'saved': asset_path(clips[role]),
    }
    defaults.set_editor_property(prop, clips[role])
LIB.set_metadata_tag(bp, 'LocomotionRevision', 'M07 LocomotionV10; only walk/chase clip references updated; user review pending')
LIB.set_metadata_tag(bp, 'LocomotionSourceManifest', str(MANIFEST))
save(bp)

report.update({
    'stage': 'M07 V10 SlowWalk and Chase clips saved into existing AI/F6 Blueprint; V09 display and other V08 actions retained; user review pending',
    'saved': True,
    'blueprint': asset_path(bp),
    'ai_and_f6_preserved': True,
    'locomotion_metadata_cdo_properties_changed': [],
    'clips': {
        role: dict(motion.get('clips', {}).get(role, {}),
                   asset=asset_path(clip), source=str(motion_files[role]),
                   duration_s=clip.get_play_length())
        for role, clip in clips.items()
    },
})
receipt()

for filename in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/filename
    # Load the latest production record at this boundary; preserve all gill,
    # geometry, cloth, nav, native build and prior action history.
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({
        'locomotion_revision': 'locomotion_v10',
        'locomotion_v10_saved': True,
        'locomotion_v10_receipt': str(REPORT),
        'locomotion_v10_source': str(MANIFEST),
        'locomotion_v10_scope': report['scope'],
        'locomotion_v10_user_review_pending': True,
        'user_review_pending': True,
        'user_accepted_motion': False,
        'runtime_tested': False,
        'visual_tested': False,
        'tested': False,
    })
    assets = record.setdefault('assets', [])
    for saved_path in report['assets']:
        if saved_path not in assets:
            assets.append(saved_path)
    if filename == 'gameplay_delivery.json':
        animations = record.setdefault('animations', {})
        animations.setdefault('clips', {}).update(report['clips'])
        animations.update({'saved': True, 'revision': 'original_v08_with_locomotion_v10',
                           'non_locomotion_revision_retained': 'original_v08',
                           'locomotion_revision': 'locomotion_v10'})
        record.setdefault('character_blueprint', {})['locomotion_clip_properties'] = {
            prop: asset_path(clips[role]) for prop, role in CLIP_PROPERTIES.items()
        }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

print('M07 V10 LOCOMOTION CLIPS AND AI/F6 REFERENCES SAVED; V09 DISPLAY, SPEEDS AND OTHER ACTIONS RETAINED; USER REVIEW PENDING', flush=True)
