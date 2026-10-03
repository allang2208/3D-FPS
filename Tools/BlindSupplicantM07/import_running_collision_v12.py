"""Save M07 arm/gill collision and two larger locomotion clips, without PIE."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
V11 = ROOT/'RecoveryHandsV11'
RUN = ROOT/'RunningV12'
COLLISION = ROOT/'ArmGillCollisionV12'
OUT = ROOT/'RunningCollisionV12'
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = RUN/'motion_manifest_v12.json'
CLOTH_MANIFEST = COLLISION/'cloth_ue_manifest_original_v12.json'
REPORT = OUT/'ue_running_collision_delivery_v12.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM_DEST = DEST+'/AnimationsRunningV12'
MESH_PATH = DEST+'/SK_M07_OriginalV12'
SIM_PATH = DEST+'/Working/SK_M07_ClothBuildSource_OriginalV12'
PHYSICS_PATH = DEST+'/PA_M07_OriginalV12'
SKELETON_PATH = DEST+'/SK_M07_ReferenceOriginalV11'
BP_PATH = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase')
CLIP_PROPERTIES = {'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase', 'walk_clip': 'Chase'}
SAVE_PATHS = {MESH_PATH, SIM_PATH, PHYSICS_PATH, BP_PATH,
              *(ANIM_DEST+'/A_M07_'+role for role in ROLES)}
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 running/collision production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving M07 running/collision assets.')

report = {
    'revision': 'running_arm_gill_collision_v12', 'saved': False, 'assets': [],
    'tested': False, 'runtime_tested': False, 'visual_tested': False,
    'user_accepted_model': False, 'user_accepted_motion': False, 'user_review_pending': True,
    'scope': 'Moving anatomical arm/hand cloth collision and coordinated larger walk/run clips and speeds',
    'reference_skeleton_reused': SKELETON_PATH, 'reference_pose_update_requested': False,
    'source_geometry_and_skin_revision_retained': 'OriginalV11',
    'gill_surface_revision_retained': 'OriginalV09',
    'materials_modified': False, 'navigation_modified': False, 'combat_timing_modified': False,
    'non_locomotion_actions_reimported': False, 'movement_speeds_modified': True,
    'motion_manifest': str(MANIFEST), 'cloth_manifest': str(CLOTH_MANIFEST),
    'changed_cdo_properties': {},
}

def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

def asset_path(asset):
    return asset.get_path_name() if asset else None

def save(asset):
    if asset is None or asset.get_path_name().split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V12 save is outside the scoped model, physics, two clips and character Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V12 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()

def mesh_options(skeleton):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('vertex_color_import_option', u.VertexColorImportOption.REPLACE)
    data.set_editor_property('use_t0_as_ref_pose', False)
    data.set_editor_property('update_skeleton_reference_pose', False)
    return options

def animation_options(skeleton, fps):
    options = mesh_options(skeleton)
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    data = options.anim_sequence_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.0
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', int(fps))
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    return options

def import_file(filename, name, destination, options, skeleton):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = destination
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+name)
    if asset is None or not task.imported_object_paths:
        raise RuntimeError('M07 V12 source did not import: '+str(filename))
    if asset.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V12 mesh/actions must use the existing corrected V11 reference.')
    return asset

display_file = V11/'SK_M07_Display_OriginalV11.fbx'
simulation_file = V11/'SK_M07_ClothBuildSource_OriginalV11.fbx'
for filename in (MANIFEST, CLOTH_MANIFEST, display_file, simulation_file):
    if not filename.is_file():
        raise RuntimeError('Complete M07 V12 production input before import: '+str(filename))
motion = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
motion_files = {}
for role in ROLES:
    clip_record = motion['clips'][role]
    filename = Path(clip_record['file'])
    if not filename.is_absolute():
        filename = MANIFEST.parent/filename
    if not filename.is_file() or not filename.resolve().is_relative_to(RUN.resolve()):
        raise RuntimeError('M07 V12 clip export is absent or outside its production directory: '+str(filename))
    motion_files[role] = filename

skeleton = u.load_asset(SKELETON_PATH)
bp = u.load_asset(BP_PATH)
materials = {
    'M07_Body': u.load_asset(DEST+'/Materials/M07_Body_OriginalV07'),
    'M07_Gills': u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07'),
}
if not skeleton or not bp or not all(materials.values()):
    raise RuntimeError('Existing V11 reference, M07 AI/F6 Blueprint and original-UV materials are required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
component = defaults.get_editor_property('mesh')
combat = defaults.get_editor_property('combat')
knockdown = defaults.get_editor_property('knockdown')
report.update({
    'stage': 'M07 V12 production import started',
    'previous_visual_mesh': asset_path(defaults.get_editor_property('visual_mesh')),
    'previous_locomotion_references': {prop: asset_path(defaults.get_editor_property(prop)) for prop in CLIP_PROPERTIES},
    'preserved_other_action_references': {
        **{prop: asset_path(defaults.get_editor_property(prop)) for prop in
           ('idle_clip', 'attack_clip', 'melee_left_clip', 'melee_right_clip', 'death_clip', 'wall_listen_clip')},
        **{'combat.'+prop: asset_path(combat.get_editor_property(prop)) for prop in ('hit_clip', 'dizzy_clip')},
        **{'knockdown.'+prop: asset_path(knockdown.get_editor_property(prop)) for prop in ('fall_clip', 'get_up_clip', 'prone_get_up_clip')},
    },
    'previous_speeds': {prop: defaults.get_editor_property(prop) for prop in
                        ('walk_speed', 'chase_speed', 'source_walk_speed', 'source_chase_speed')},
    'preserved_combat_settings': {prop: defaults.get_editor_property(prop) for prop in
                                 ('left_contact_time', 'right_contact_time', 'contact_time', 'contact_end',
                                  'contact_window_seconds', 'animation_blend_seconds')},
})
receipt()

existing_mesh = u.load_asset(MESH_PATH)
if existing_mesh:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing_mesh)
mesh = import_file(display_file, 'SK_M07_OriginalV12', DEST, mesh_options(skeleton), skeleton)
simulation = import_file(simulation_file, 'SK_M07_ClothBuildSource_OriginalV12',
                         DEST+'/Working', mesh_options(skeleton), skeleton)
slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    material_name = 'M07_Body' if name == 'M07_Identity' else name
    if material_name not in materials:
        raise RuntimeError('M07 V12 display contains an unassigned material slot: '+name)
    slot.material_interface = materials[material_name]
mesh.set_editor_property('materials', slots)
physics = json.loads(u.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
if not physics.get('success'):
    raise RuntimeError('M07 V12 matching body collision authoring failed: '+json.dumps(physics))
report.update({'mesh_imported': asset_path(mesh), 'simulation_imported': asset_path(simulation),
               'body_physics_authored': physics})
receipt()
print('M07_V12_COLLISION_IMPORT_INPUTS '+json.dumps({'mesh': asset_path(mesh),
      'simulation': asset_path(simulation), 'body_physics': physics}, ensure_ascii=False), flush=True)
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(
    mesh, simulation, str(CLOTH_MANIFEST)))
if not cloth.get('success'):
    raise RuntimeError('M07 V12 interacting gill cloth authoring failed: '+json.dumps(cloth))
LIB.set_metadata_tag(mesh, 'SourceRevision', 'M07 V12 moving arm/gill collision; OriginalV11 mesh/skin and reference, OriginalV09 membranes; user review pending')
LIB.set_metadata_tag(mesh, 'ArmGillCollisionManifest', str(CLOTH_MANIFEST))
save(mesh)
save(simulation)
save(u.load_asset(PHYSICS_PATH))
physics.update({'saved': True, 'caller_must_save_packages': False})
cloth.update({'saved': True, 'caller_must_save_package': False, 'tested': False})
report.update({'stage': 'M07 V12 model, cloth and body collision saved; locomotion and Blueprint pending',
               'mesh': asset_path(mesh), 'simulation_mesh': asset_path(simulation), 'skeleton': asset_path(skeleton),
               'body_physics': physics, 'cloth': cloth, 'display_source': str(display_file),
               'simulation_source': str(simulation_file)})
receipt()

clips = {}
for role in ROLES:
    clip_record = motion['clips'][role]
    clip = import_file(motion_files[role], 'A_M07_'+role, ANIM_DEST,
                       animation_options(skeleton, clip_record.get('fps', motion.get('fps', 30))), skeleton)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.0)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'M07 RunningV12 larger coordinated human locomotion; corrected V11 reference; user review pending')
    LIB.set_metadata_tag(clip, 'LocomotionSourceManifest', str(MANIFEST))
    LIB.set_metadata_tag(clip, 'LocomotionContract', json.dumps(clip_record, ensure_ascii=False))
    save(clip)
    clips[role] = clip

defaults.set_editor_property('visual_mesh', mesh)
component.set_skeletal_mesh_asset(mesh)
report['changed_cdo_properties']['visual_mesh'] = {'previous': report['previous_visual_mesh'], 'saved': asset_path(mesh)}
for prop, role in CLIP_PROPERTIES.items():
    defaults.set_editor_property(prop, clips[role])
    report['changed_cdo_properties'][prop] = {'previous': report['previous_locomotion_references'][prop], 'saved': asset_path(clips[role])}
speeds = {'walk_speed': 160.0, 'chase_speed': 360.0,
          'source_walk_speed': 160.0, 'source_chase_speed': 360.0}
for prop, value in speeds.items():
    defaults.set_editor_property(prop, value)
    report['changed_cdo_properties'][prop] = {'previous': report['previous_speeds'][prop], 'saved': value}
defaults.get_editor_property('character_movement').set_editor_property('max_walk_speed', speeds['chase_speed'])
LIB.set_metadata_tag(bp, 'LocomotionRevision', 'M07 RunningV12; SlowWalk160 Chase360 cm/s; larger coordinated arm/leg motion; user review pending')
LIB.set_metadata_tag(bp, 'LocomotionSourceManifest', str(MANIFEST))
LIB.set_metadata_tag(bp, 'ArmGillCollisionManifest', str(CLOTH_MANIFEST))
save(bp)
report.update({
    'stage': 'M07 V12 arm/gill cloth collision, two walk/run clips, speeds and AI/F6 Blueprint saved; user review pending',
    'saved': True, 'blueprint': asset_path(bp), 'ai_and_f6_preserved': True,
    'speeds_cm_s': speeds,
    'clips': {role: dict(motion['clips'][role], asset=asset_path(clip), source=str(motion_files[role]),
                         duration_s=clip.get_play_length()) for role, clip in clips.items()},
})
receipt()
for filename in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/filename
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({
        'revision': 'OriginalV12RunningAndCollision', 'geometry_revision': 'OriginalV11',
        'stage': report['stage'], 'mesh': report['mesh'], 'skeleton': report['skeleton'],
        'running_collision_v12_saved': True, 'running_collision_v12_receipt': str(REPORT),
        'ue_save_receipt': str(REPORT), 'locomotion_revision': 'running_v12',
        'locomotion_source': str(MANIFEST), 'arm_gill_collision_manifest': str(CLOTH_MANIFEST),
        'animation_stage': 'Ten V11 non-locomotion actions retained; V12 larger SlowWalk/Chase clips and matched speeds saved',
        'animation_revision_retained': 'OriginalV11 non-locomotion actions and corrected reference',
        'motion_authoring_receipt': str(MANIFEST),
        'body_physics_receipt': str(REPORT), 'interacting_gills_receipt': str(REPORT),
        'active_animation_source': str(RUN/'M07_Original_Running_V12.blend'),
        'active_cloth_collision_source': str(CLOTH_MANIFEST),
        'body_physics': physics, 'interacting_gills': cloth, 'speeds_cm_s': speeds,
        'user_review_pending': True, 'user_accepted_model': False, 'user_accepted_motion': False,
        'runtime_tested': False, 'visual_tested': False, 'tested': False,
    })
    assets = record.setdefault('assets', [])
    for saved_path in report['assets']:
        if saved_path not in assets:
            assets.append(saved_path)
    if filename == 'gameplay_delivery.json':
        character = record.setdefault('character_blueprint', {})
        character.update({'mesh': report['mesh'], 'locomotion_clip_properties':
                          {prop: asset_path(clips[role]) for prop, role in CLIP_PROPERTIES.items()},
                          'speeds_cm_s': speeds})
        character.setdefault('clip_properties', {}).update({prop: asset_path(clips[role]) for prop, role in CLIP_PROPERTIES.items()})
        animations = record.setdefault('animations', {})
        animations.update({'saved': True, 'revision': 'original_v11_with_running_v12',
                           'reference_revision': 'original_v11', 'non_locomotion_revision_retained': 'original_v11',
                           'locomotion_revision': 'running_v12'})
        animations.setdefault('clips', {}).update(report['clips'])
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07 V12 ARM/GILL COLLISION, TWO LOCOMOTION CLIPS, SPEEDS AND AI/F6 REFERENCES SAVED; USER REVIEW PENDING', flush=True)
