"""Save the original-source M-07 hand/arm repair and its twelve actions.

The V11 display, hidden cloth meshes and all actions share one new centimeter
OriginalV11 reference with corrected upperarm axes. V09 membrane/proxy work, V07 original-UV
materials, V10 gait timing, movement speeds and combat contacts are retained.
Only the M07 character's visual mesh and action references are replaced.
This production entry never opens a preview, starts PIE or runs a test.
"""
import json
from pathlib import Path

import unreal as u


PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
SOURCE = ROOT/'RecoveryHandsV11'
MANIFEST = SOURCE/'rig_motion/motion_manifest_v11.json'
DELIVERY = SOURCE/'hand_arm_delivery_v11.json'
REPORT = SOURCE/'ue_hand_arm_delivery_v11.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM_DEST = DEST+'/AnimationsOriginalV11'
SKELETON_PATH = DEST+'/SK_M07_ReferenceOriginalV11'
MESH_PATH = DEST+'/SK_M07_OriginalV11'
SIMULATION_PATH = DEST+'/Working/SK_M07_ClothBuildSource_OriginalV11'
PHYSICS_PATH = DEST+'/PA_M07_OriginalV11'
BP_PATH = DEST+'/BP_BlindSupplicantM07'
ROLES = ('Idle', 'SlowWalk', 'Chase', 'MeleeLeft', 'MeleeRight', 'Hit',
         'Death', 'WallListen', 'Dizzy', 'Fall', 'GetUp', 'ProneGetUp')
CLIP_PROPERTIES = {
    'idle_clip': 'Idle', 'walk_clip': 'Chase', 'attack_clip': 'MeleeLeft',
    'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase',
    'melee_left_clip': 'MeleeLeft', 'melee_right_clip': 'MeleeRight',
    'death_clip': 'Death', 'wall_listen_clip': 'WallListen',
}
COMBAT_CLIP_PROPERTIES = {'hit_clip': 'Hit', 'dizzy_clip': 'Dizzy'}
KNOCKDOWN_CLIP_PROPERTIES = {
    'fall_clip': 'Fall', 'get_up_clip': 'GetUp',
    'prone_get_up_clip': 'ProneGetUp',
}
SAVE_PATHS = {
    MESH_PATH, SIMULATION_PATH, PHYSICS_PATH, BP_PATH, SKELETON_PATH,
    *(ANIM_DEST+'/A_M07_'+role for role in ROLES),
}
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V11 original hand/arm production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving the M07 original hand/arm repair.')

report = {
    'revision': 'original_hands_arms_v11',
    'scope': 'Local original-source hand/arm surface and skin repair, with matching twelve action exports',
    'saved': False,
    'assets': [],
    'tested': False,
    'runtime_tested': False,
    'visual_tested': False,
    'user_accepted_model': False,
    'user_accepted_motion': False,
    'user_review_pending': True,
    'original_model': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
    'feedback_image': 'C:/Users/allan/AppData/Local/Temp/codex-clipboard-97d042b6-1656-423f-a103-860c26795253.png',
    'source_delivery': str(DELIVERY),
    'motion_source': str(MANIFEST),
    'reference_skeleton': SKELETON_PATH,
    'reference_axis_correction': 'Both upperarm local Y axes now follow the retained shoulder/elbow joint positions; all twelve clips and meshes share that reference',
    'reference_pose_update_requested': False,
    'gill_authoring_revision_retained': 'original_gills_v09',
    'gait_timing_revision_retained': 'locomotion_v10',
    'materials_modified': False,
    'navigation_modified': False,
    'movement_speeds_modified': False,
    'combat_timing_modified': False,
    'changed_cdo_properties': {},
}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def asset_path(asset):
    return asset.get_path_name() if asset else None


def save(asset):
    # Only the new matching skeleton and this model/actions/BP are saved.
    if asset is None or asset.get_path_name().split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V11 hand/arm production cannot save a package outside its new model/actions and existing character Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V11 package did not save: '+asset.get_path_name())
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
        raise RuntimeError('M07 V11 source did not import: '+str(filename))
    if skeleton is not None and asset.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V11 model and actions must share the new OriginalV11 reference skeleton.')
    return asset


def motion_inputs():
    if not MANIFEST.is_file():
        raise RuntimeError('Complete the V11 rig_motion/motion_manifest_v11.json export before UE import.')
    motion = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    files = {}
    for role in ROLES:
        clip = motion.get('clips', {}).get(role, {})
        filename = Path(clip['file']) if clip.get('file') else MANIFEST.parent/('A_M07_'+role+'.fbx')
        if not filename.is_absolute():
            relative = filename
            filename = MANIFEST.parent/relative
            if not filename.is_file():
                filename = SOURCE/relative
        if not filename.is_file() or not filename.resolve().is_relative_to(SOURCE.resolve()):
            raise RuntimeError('M07 V11 '+role+' export is absent or outside its production directory: '+str(filename))
        files[role] = filename
    return motion, files


def editable_source(source_authoring):
    # Source authoring chooses the actual master name. Avoid reporting a
    # guessed blend path when the export manifest names it differently.
    for key in ('saved_source', 'editable_source', 'combined_editable_source', 'master_blend', 'blend_file', 'blend'):
        value = source_authoring.get(key)
        if isinstance(value, str):
            path = Path(value)
            if not path.is_absolute():
                path = SOURCE/path
            if path.suffix.lower() == '.blend' and path.is_file() and path.resolve().is_relative_to(SOURCE.resolve()):
                return str(path)
    candidates = list(SOURCE.glob('M07*.blend'))
    return str(candidates[0]) if len(candidates) == 1 else None


display_file = SOURCE/'SK_M07_Display_OriginalV11.fbx'
simulation_file = SOURCE/'SK_M07_ClothBuildSource_OriginalV11.fbx'
cloth_file = SOURCE/'cloth_ue_manifest_original_v11.json'
for filename in (display_file, simulation_file, cloth_file, DELIVERY):
    if not filename.is_file():
        raise RuntimeError('Complete the original V11 hand/arm export before UE import: '+str(filename))
motion, motion_files = motion_inputs()
source_authoring = json.loads(DELIVERY.read_text(encoding='utf-8-sig'))
skeleton = u.load_asset(SKELETON_PATH)
bp = u.load_asset(BP_PATH)
materials = {
    'M07_Body': u.load_asset(DEST+'/Materials/M07_Body_OriginalV07'),
    'M07_Gills': u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07'),
}
if not bp or not all(materials.values()):
    raise RuntimeError('The existing M07 AI/F6 Blueprint and original-UV V07 materials are required.')

u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
component = defaults.get_editor_property('mesh')
combat = defaults.get_editor_property('combat')
knockdown = defaults.get_editor_property('knockdown')
report.update({
    'stage': 'M07 V11 hand/arm model and matching action production started',
    'source_authoring': source_authoring,
    'materials_reused': {name: asset_path(asset) for name, asset in materials.items()},
    'previous_visual_mesh': asset_path(defaults.get_editor_property('visual_mesh')),
    'preserved_component_references': {
        'component': asset_path(component),
        'previous_skeletal_mesh': asset_path(component.get_skeletal_mesh_asset()),
        'anim_class': asset_path(component.get_editor_property('anim_class')),
        'override_materials': [asset_path(asset) for asset in component.get_editor_property('override_materials')],
        'ai_controller_class': asset_path(defaults.get_editor_property('ai_controller_class')),
    },
    'preserved_settings': {
        prop: defaults.get_editor_property(prop)
        for prop in ('walk_speed', 'chase_speed', 'source_walk_speed', 'source_chase_speed',
                     'left_contact_time', 'right_contact_time', 'contact_time',
                     'contact_end', 'contact_window_seconds', 'animation_blend_seconds')
    },
    'previous_clip_references': {
        **{prop: asset_path(defaults.get_editor_property(prop)) for prop in CLIP_PROPERTIES},
        **{'combat.'+prop: asset_path(combat.get_editor_property(prop)) for prop in COMBAT_CLIP_PROPERTIES},
        **{'knockdown.'+prop: asset_path(knockdown.get_editor_property(prop)) for prop in KNOCKDOWN_CLIP_PROPERTIES},
    },
})
master_source = editable_source(source_authoring)
if master_source:
    report['editable_source'] = master_source
receipt()

existing_mesh = u.load_asset(MESH_PATH)
if existing_mesh:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing_mesh)
mesh = import_file(display_file, 'SK_M07_OriginalV11', DEST, mesh_options(skeleton), skeleton)
skeleton = mesh.skeleton
if skeleton.get_name() != 'SK_M07_ReferenceOriginalV11':
    if not AT.rename_assets([u.AssetRenameData(skeleton, DEST, 'SK_M07_ReferenceOriginalV11')]):
        raise RuntimeError('The matching OriginalV11 reference skeleton could not be named.')
    skeleton = u.load_asset(SKELETON_PATH)
save(skeleton)
simulation = import_file(simulation_file, 'SK_M07_ClothBuildSource_OriginalV11',
                         DEST+'/Working', mesh_options(skeleton), skeleton)

slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    material_name = 'M07_Body' if name == 'M07_Identity' else name
    if material_name not in materials:
        raise RuntimeError('OriginalV11 display contains an unassigned material slot: '+name)
    slot.material_interface = materials[material_name]
mesh.set_editor_property('materials', slots)

physics = json.loads(u.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
if not physics.get('success'):
    raise RuntimeError('OriginalV11 matching body collision authoring failed: '+json.dumps(physics))
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(
    mesh, simulation, str(cloth_file)))
if not cloth.get('success'):
    raise RuntimeError('OriginalV11 retained original gill cloth binding failed: '+json.dumps(cloth))

LIB.set_metadata_tag(mesh, 'SourceRevision', 'M07 OriginalV11: local original hand/arm repair; matching corrected V11 upperarm reference and retained V09 gills; user review pending')
LIB.set_metadata_tag(mesh, 'SourceModel', report['original_model'])
LIB.set_metadata_tag(mesh, 'HandArmRepairSource', str(DELIVERY))
LIB.set_metadata_tag(mesh, 'Cloth', 'V09 original gill display and hidden six-island proxy retained; repaired capture and matching V11 body collision')
save(mesh)
save(simulation)
save(u.load_asset(PHYSICS_PATH))
physics.update({'saved': True, 'caller_must_save_packages': False})
cloth.update({'saved': True, 'caller_must_save_package': False, 'tested': False})
report.update({
    'stage': 'M07 V11 original hand/arm model, retained gill cloth and matching body collision saved; action and Blueprint update pending',
    'mesh': asset_path(mesh),
    'simulation_mesh': asset_path(simulation),
    'skeleton': asset_path(skeleton),
    'body_physics': physics,
    'cloth': cloth,
    'display_source': str(display_file),
    'simulation_source': str(simulation_file),
    'cloth_manifest': str(cloth_file),
})
receipt()

clips = {}
for role in ROLES:
    clip_record = motion.get('clips', {}).get(role, {})
    clip = import_file(motion_files[role], 'A_M07_'+role, ANIM_DEST,
                       animation_options(skeleton, clip_record.get('fps', motion.get('fps', 30))), skeleton)
    # This assigns a preview reference without opening or playing a preview.
    clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'M07 OriginalV11 hand/arm motion repair; corrected V11 reference and retained V10 gait timing; user review pending')
    LIB.set_metadata_tag(clip, 'HandArmMotionManifest', str(MANIFEST))
    save(clip)
    clips[role] = clip
save(skeleton)

# Only these references change. Keep the existing animation class, AI,
# material overrides, movement calibration and attack contact windows.
defaults.set_editor_property('visual_mesh', mesh)
component.set_skeletal_mesh_asset(mesh)
report['changed_cdo_properties']['visual_mesh'] = {
    'previous': report['previous_visual_mesh'], 'saved': asset_path(mesh),
}
for owner, prefix, properties in ((defaults, '', CLIP_PROPERTIES),
                                  (combat, 'combat.', COMBAT_CLIP_PROPERTIES),
                                  (knockdown, 'knockdown.', KNOCKDOWN_CLIP_PROPERTIES)):
    for prop, role in properties.items():
        key = prefix+prop
        report['changed_cdo_properties'][key] = {
            'previous': report['previous_clip_references'][key],
            'saved': asset_path(clips[role]),
        }
        owner.set_editor_property(prop, clips[role])
LIB.set_metadata_tag(bp, 'SourceRevision', 'M07 OriginalV11 original hand/arm repair and matching twelve actions; AI/F6, V10 gait speeds/contact timing retained; user review pending')
LIB.set_metadata_tag(bp, 'HandArmRepairSource', str(DELIVERY))
LIB.set_metadata_tag(bp, 'HandArmMotionManifest', str(MANIFEST))
save(bp)

report.update({
    'stage': 'M07 OriginalV11 local original hand/arm model, gill cloth, body collision and twelve actions saved into existing AI/F6 Blueprint; user review pending',
    'saved': True,
    'blueprint': asset_path(bp),
    'ai_and_f6_preserved': True,
    'reference_units': 'Matching OriginalV11 centimeter bones and vertices; armature object scale 1; frame-zero reference excluded from action clips',
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
    # Read the latest production record now, retaining navigation, provenance,
    # prior repair history and independent work rather than replacing it.
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({
        'revision': 'OriginalV11HandsAndArms',
        'geometry_revision': 'OriginalV11',
        'stage': report['stage'],
        'mesh': report['mesh'],
        'skeleton': report['skeleton'],
        'original_v11_saved': True,
        'original_v11_receipt': str(REPORT),
        'hand_arm_revision': 'original_hands_arms_v11',
        'hand_arm_repair_source': str(DELIVERY),
        'hand_arm_repair_receipt': str(REPORT),
        'hand_arm_repair_scope': report['scope'],
        'hand_arm_source_authoring': source_authoring,
        'user_reported_hand_arm_spikes': True,
        'editable_source_revision': str(SOURCE),
        'display_export': str(display_file),
        'cloth_construction_export': str(simulation_file),
        'ue_save_receipt': str(REPORT),
        'motion_authoring_receipt': str(MANIFEST),
        'animation_stage': 'Twelve OriginalV11 actions saved on corrected OriginalV11 reference; V10 gait timing retained',
        'animation_revision_retained': 'LocomotionV10 gait timing',
        'locomotion_revision': 'original_v11_with_v10_gait_timing',
        'body_physics': physics,
        'interacting_gills': cloth,
        'body_physics_receipt': str(REPORT),
        'interacting_gills_receipt': str(REPORT),
        'gill_authoring_revision_retained': 'original_gills_v09',
        'user_review_pending': True,
        'user_accepted_model': False,
        'user_accepted_motion': False,
        'runtime_tested': False,
        'visual_tested': False,
        'tested': False,
        'claimed_visual_fix': False,
    })
    if master_source:
        relative_master = str(Path(master_source).relative_to(ROOT)).replace('\\', '/')
        record.update({'editable_source': relative_master,
                       'combined_editable_source': relative_master,
                       'active_authoring_source': relative_master})
    assets = record.setdefault('assets', [])
    for saved_path in report['assets']:
        if saved_path not in assets:
            assets.append(saved_path)
    if filename == 'gameplay_delivery.json':
        character = record.setdefault('character_blueprint', {})
        character.update({'mesh': report['mesh'],
                          'clip_properties': {prop: asset_path(clips[role]) for prop, role in CLIP_PROPERTIES.items()},
                          'locomotion_clip_properties': {prop: asset_path(clips[role]) for prop, role in CLIP_PROPERTIES.items()
                                                         if prop in ('slow_walk_clip', 'chase_clip', 'walk_clip')}})
        record['animations'] = {'saved': True, 'revision': 'original_v11',
                                'reference_revision': 'original_v11',
                                'gait_timing_revision_retained': 'locomotion_v10',
                                'clips': report['clips']}
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')

print('M07 ORIGINALV11 ORIGINAL HAND/ARM MODEL, RETAINED GILLS, TWELVE ACTIONS AND AI/F6 REFERENCES SAVED; USER REVIEW PENDING', flush=True)
