"""Import the original Meshy M-07 body, membranes and matching authored motion.

Creates independent OriginalV06 mesh/skeleton/cloth/physics/animation packages,
then saves their references into the existing AI/F6 Blueprint. This production
entry never starts PIE, plays simulation or performs a visual/runtime test.
"""
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
SOURCE = ROOT/'RecoveryOriginalV06'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM_DEST = DEST+'/AnimationsOriginalV06'
REPORT = SOURCE/'ue_original_delivery_v06.json'
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
ROLES = ('Idle', 'SlowWalk', 'Chase', 'MeleeLeft', 'MeleeRight', 'Hit',
         'Death', 'WallListen', 'Dizzy', 'Fall', 'GetUp', 'ProneGetUp')

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 OriginalV06 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving the original-source M07 candidate.')

report = {'revision': 'original_v06', 'saved': False, 'assets': [],
          'runtime_tested': False, 'visual_tested': False, 'tested': False,
          'user_accepted_model': False,
          'previous_revision_rejected_by_user': 'V05 rebuilt anatomy and membranes rejected; restart from the supplied original GLB',
          'original_model': 'C:/Users/allan/Downloads/Meshy_AI_Veilwing_07_1001123357_texture.glb',
          'visible_geometry_source': 'Original Meshy body, sensory head, limbs, equipment and gill surfaces; no donor display body'}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not asset or not asset.get_path_name().startswith(DEST+'/'):
        raise RuntimeError('M07 original-source authoring cannot save a package outside its ownership.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 OriginalV06 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()


def import_file(filename, name, destination, options, factory):
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = destination
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.factory = factory
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+name)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('M07 OriginalV06 source did not import: '+str(filename))
    return asset


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
    data.set_editor_property('custom_sample_rate', fps)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    return options


def motion_inputs():
    # Only this new original-source production directory may supply animation.
    # The old reconstructed body/action packages are never used as a fallback.
    directories = (SOURCE/'rig_motion'/'Delivery', SOURCE/'rig_motion', SOURCE)
    manifest_path = next((directory/'motion_manifest.json' for directory in directories
                          if (directory/'motion_manifest.json').is_file()), None)
    if manifest_path is None:
        raise RuntimeError('Export the matching OriginalV06 motion_manifest.json before UE import.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    files = {}
    for role in ROLES:
        clip = manifest.get('clips', {}).get(role, {})
        authored = clip.get('file') if isinstance(clip, dict) else None
        filename = Path(authored) if authored else None
        if filename and not filename.is_absolute():
            filename = manifest_path.parent/filename
        if filename is None:
            filename = next((directory/('A_M07_'+role+'.fbx') for directory in directories
                             if (directory/('A_M07_'+role+'.fbx')).is_file()), None)
        if filename is None or not filename.is_file() or not filename.resolve().is_relative_to(SOURCE.resolve()):
            raise RuntimeError('Required OriginalV06 '+role+' export is absent or outside its original-source production directory.')
        files[role] = filename
    return manifest_path, manifest, files


motion_path, motion, motion_files = motion_inputs()
display_file = SOURCE/'SK_M07_Display_OriginalV06.fbx'
simulation_file = SOURCE/'SK_M07_ClothBuildSource_OriginalV06.fbx'
cloth_file = SOURCE/'cloth_ue_manifest_original_v06.json'
for filename in (display_file, simulation_file, cloth_file):
    if not filename.is_file():
        raise RuntimeError('Complete the original-source M07 export before import: '+str(filename))

materials = {name: u.load_asset(DEST+'/Materials/'+name) for name in ('M07_Body', 'M07_Gills')}
if not all(materials.values()):
    raise RuntimeError('The original M07 PBR body and gill materials must exist before OriginalV06 import.')
bp = u.load_asset(DEST+'/BP_BlindSupplicantM07')
ai = u.load_class(None, '/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C')
if not bp or not ai:
    raise RuntimeError('The existing M07 AI/F6 character and shared monster controller must be retained.')

existing_mesh = u.load_asset(DEST+'/SK_M07_OriginalV06')
if existing_mesh:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing_mesh)
existing_skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV06')
mesh = import_file(display_file, 'SK_M07_OriginalV06', DEST,
                   mesh_options(existing_skeleton), u.FbxFactory())
skeleton = mesh.skeleton
if skeleton.get_name() != 'SK_M07_ReferenceOriginalV06':
    if not AT.rename_assets([u.AssetRenameData(skeleton, DEST, 'SK_M07_ReferenceOriginalV06')]):
        raise RuntimeError('The fresh OriginalV06 reference skeleton could not be named.')
    skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV06')
save(skeleton)
simulation = import_file(simulation_file, 'SK_M07_ClothBuildSource_OriginalV06', DEST+'/Working',
                         mesh_options(skeleton), u.FbxFactory())

slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    material_name = 'M07_Body' if name == 'M07_Identity' else name
    if material_name not in materials:
        raise RuntimeError('OriginalV06 display contains an unassigned production material slot: '+name)
    slot.material_interface = materials[material_name]
mesh.set_editor_property('materials', slots)

physics = json.loads(u.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
if not physics.get('success'):
    raise RuntimeError('OriginalV06 body collision authoring failed: '+json.dumps(physics))
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(
    mesh, simulation, str(cloth_file)))
if not cloth.get('success'):
    raise RuntimeError('OriginalV06 original gill binding failed: '+json.dumps(cloth))
LIB.set_metadata_tag(mesh, 'SourceRevision', 'M07 OriginalV06: original Meshy display body and gills with new reference rig/weights; user review pending')
LIB.set_metadata_tag(mesh, 'SourceModel', report['original_model'])
LIB.set_metadata_tag(mesh, 'Cloth', 'Original gill display surfaces; separate hidden six-island simulation proxy; matching OriginalV06 body collision')
save(mesh)
save(simulation)
save(u.load_asset(DEST+'/PA_M07_OriginalV06'))
save(skeleton)
physics.update({'saved': True, 'caller_must_save_packages': False})
cloth.update({'saved': True, 'caller_must_save_package': False})
report.update({'stage': 'OriginalV06 original body, gills, matching collision and cloth saved',
               'mesh': mesh.get_path_name(), 'cloth': cloth, 'body_physics': physics,
               'display_source': str(display_file), 'simulation_source': str(simulation_file),
               'cloth_manifest': str(cloth_file)})
receipt()

clips = {}
for role in ROLES:
    clip = import_file(motion_files[role], 'A_M07_'+role, ANIM_DEST,
                       animation_options(skeleton, motion.get('fps', 30)), u.FbxFactory())
    clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'M07 OriginalV06 motion on the original-source reference rig; user review pending')
    save(clip)
    clips[role] = clip
save(skeleton)

u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
defaults.set_editor_property('visual_mesh', mesh)
component = defaults.get_editor_property('mesh')
component.set_skeletal_mesh_asset(mesh)
component.set_editor_property('override_materials', [])
component.set_anim_instance_class(u.BlindSupplicantAnimInstance)
defaults.set_editor_property('ai_controller_class', ai)
for prop, role in [('idle_clip', 'Idle'), ('walk_clip', 'Chase'), ('attack_clip', 'MeleeLeft'),
                   ('slow_walk_clip', 'SlowWalk'), ('chase_clip', 'Chase'), ('melee_left_clip', 'MeleeLeft'),
                   ('melee_right_clip', 'MeleeRight'), ('death_clip', 'Death'), ('wall_listen_clip', 'WallListen')]:
    defaults.set_editor_property(prop, clips[role])

motion_clips = motion.get('clips', {})
defaults.set_editor_property('source_walk_speed', motion_clips.get('SlowWalk', {}).get('expected_speed_cm_s', 90.0))
defaults.set_editor_property('source_chase_speed', motion_clips.get('Chase', {}).get('expected_speed_cm_s', 145.0))
left_contact = motion_clips.get('MeleeLeft', {}).get('impact_seconds', .68)
right_contact = motion_clips.get('MeleeRight', {}).get('impact_seconds', .78)
defaults.set_editor_property('left_contact_time', left_contact)
defaults.set_editor_property('right_contact_time', right_contact)
defaults.set_editor_property('contact_time', left_contact)
defaults.set_editor_property('contact_end', left_contact+defaults.get_editor_property('contact_window_seconds'))
combat = defaults.get_editor_property('combat')
combat.set_editor_property('hit_clip', clips['Hit'])
combat.set_editor_property('dizzy_clip', clips['Dizzy'])
knockdown = defaults.get_editor_property('knockdown')
for prop, role in [('fall_clip', 'Fall'), ('get_up_clip', 'GetUp'), ('prone_get_up_clip', 'ProneGetUp')]:
    knockdown.set_editor_property(prop, clips[role])
LIB.set_metadata_tag(bp, 'SourceRevision', 'M07 OriginalV06: preserved original Meshy character with separate cloth proxy; user review pending')
save(bp)

report.update({'stage': 'M07 OriginalV06 original-source mesh, cloth, collision, 12 actions and existing AI/F6 Blueprint saved; user review pending',
    'saved': True, 'blueprint': bp.get_path_name(), 'ai_and_f6_preserved': True,
    'ai_controller_class': ai.get_path_name(), 'skeleton': skeleton.get_path_name(),
    'reference_units': 'centimeter bones and vertices; armature object scale 1; frame-zero reference exported outside clips',
    'clips': {role: {'asset': clip.get_path_name(), 'source': str(motion_files[role]), 'duration_s': clip.get_play_length()} for role, clip in clips.items()},
    'motion_source': str(motion_path), 'user_review_pending': True})
receipt()
for filename in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/filename
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({'stage': report['stage'], 'mesh': report['mesh'], 'original_v06_saved': True,
        'anatomy_v05_rejected_by_user': True, 'original_v06_receipt': str(REPORT),
        'runtime_tested': False, 'visual_tested': False, 'tested': False,
        'user_accepted_model': False, 'current_display_asset_requires_repair': False,
        'user_review_pending': True, 'interacting_gills': cloth, 'body_physics': physics})
    if filename == 'gameplay_delivery.json':
        record['character_blueprint']['mesh'] = report['mesh']
        record['animations'] = {'saved': True, 'revision': 'original_v06', 'clips': report['clips']}
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07 ORIGINALV06 ORIGINAL-SOURCE MODEL, CLOTH AND AI/F6 REFERENCES SAVED; USER REVIEW PENDING', flush=True)
