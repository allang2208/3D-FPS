"""Background production import/save of original-surface M07 V13. No PIE."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'RecoveryOriginalV13'
REPORT = OUT/'ue_delivery_v13.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
MESH = DEST+'/SK_M07_OriginalV13'
SIM = DEST+'/Working/SK_M07_ClothBuildSource_OriginalV13'
PHYSICS = DEST+'/PA_M07_OriginalV13'
SKELETON = DEST+'/SK_M07_ReferenceOriginalV11'
BP = DEST+'/BP_BlindSupplicantM07'
ANIM = DEST+'/AnimationsOriginalV13'
MANIFEST = OUT/'motion_manifest_v13.json'
CLOTH_MANIFEST = OUT/'cloth_ue_manifest_original_v13.json'
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
motion = json.loads(MANIFEST.read_text(encoding='utf-8'))
roles = tuple(motion['clips'])
save_paths = {MESH, SIM, PHYSICS, BP, *(ANIM+'/A_M07_'+role for role in roles)}
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('V13 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; V13 saving deferred.')

report = {'revision': 'OriginalV13', 'saved': False, 'assets': [], 'stage': 'production import started',
          'original_model_reconstructed': False, 'reference_pose_update_requested': False,
          'motion_manifest': str(MANIFEST), 'cloth_manifest': str(CLOTH_MANIFEST),
          'runtime_tested': False, 'visual_tested': False, 'tested': False,
          'user_accepted': False, 'user_review_pending': True}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def path(asset):
    return asset.get_path_name() if asset else None


def save(asset):
    if not asset or asset.get_path_name().split('.', 1)[0] not in save_paths:
        raise RuntimeError('V13 save outside the scoped candidate, clips and existing M07 Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('V13 asset did not save: '+asset.get_path_name())
    if path(asset) not in report['assets']:
        report['assets'].append(path(asset))
    receipt()


def options(skeleton, animation=False):
    value = u.FbxImportUI()
    value.automated_import_should_detect_type = False
    value.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    value.import_as_skeletal = True
    value.import_mesh = not animation
    value.import_animations = animation
    value.import_materials = False
    value.import_textures = False
    value.create_physics_asset = False
    value.skeleton = skeleton
    data = value.anim_sequence_import_data if animation else value.skeletal_mesh_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.
    if animation:
        data.set_editor_property('use_default_sample_rate', False)
        data.set_editor_property('custom_sample_rate', 30)
        data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('preserve_local_transform', True)
    else:
        data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.set_editor_property('vertex_color_import_option', u.VertexColorImportOption.REPLACE)
        data.set_editor_property('use_t0_as_ref_pose', False)
        data.set_editor_property('update_skeleton_reference_pose', False)
    return value


def import_file(filename, asset_name, destination, skeleton, animation=False):
    filename = Path(filename)
    if not filename.is_file() or not filename.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError('V13 production input absent or outside its source directory: '+str(filename))
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = asset_name
    task.destination_path = destination
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options(skeleton, animation)
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+asset_name)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('V13 production import failed: '+str(filename))
    if asset.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('V13 sources must reuse the unchanged V11 reference skeleton.')
    return asset


skeleton = u.load_asset(SKELETON)
bp = u.load_asset(BP)
materials = {'M07_Body': u.load_asset(DEST+'/Materials/M07_Body_OriginalV07'),
             'M07_Gills': u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07')}
if not skeleton or not bp or not all(materials.values()):
    raise RuntimeError('Existing M07 reference, materials and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
report['previous_mesh'] = path(defaults.get_editor_property('visual_mesh'))
report['previous_clip_references'] = {}
receipt()
existing = u.load_asset(MESH)
if existing:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing)
mesh = import_file(OUT/'SK_M07_Display_OriginalV13.fbx', 'SK_M07_OriginalV13', DEST, skeleton)
simulation = import_file(OUT/'SK_M07_ClothBuildSource_OriginalV13.fbx', 'SK_M07_ClothBuildSource_OriginalV13', DEST+'/Working', skeleton)
slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    name = 'M07_Body' if name == 'M07_Identity' else name
    if name not in materials:
        raise RuntimeError('Unassigned V13 original-UV material slot: '+name)
    slot.material_interface = materials[name]
mesh.set_editor_property('materials', slots)
physics = json.loads(u.BlindSupplicantPhysicsAuthoring.build_body_physics(mesh))
if not physics.get('success'):
    raise RuntimeError('V13 body physics authoring failed: '+json.dumps(physics))
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(mesh, simulation, str(CLOTH_MANIFEST)))
if not cloth.get('success'):
    raise RuntimeError('V13 cloth authoring failed: '+json.dumps(cloth))
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not u.BlindSupplicantAuthoring.configure_distance_lods(mesh):
    raise RuntimeError('V13 distant LOD authoring refused this candidate.')
if not editor.regenerate_lod(mesh, 3, False, False):
    raise RuntimeError('V13 distant LOD generation failed.')
report['generated_lods'] = [{'lod': i, 'vertices': editor.get_num_verts(mesh, i),
                             'sections': editor.get_num_sections(mesh, i)} for i in range(editor.get_lod_count(mesh))]
LIB.set_metadata_tag(mesh, 'SourceRevision', 'OriginalV13 original body local leg skin, original UV leaves reduced, bounded low-density cloth; user review pending')
LIB.set_metadata_tag(mesh, 'ArmGillCollisionManifest', str(CLOTH_MANIFEST))
save(mesh)
save(simulation)
save(u.load_asset(PHYSICS))
physics.update({'saved': True, 'caller_must_save_packages': False})
cloth.update({'saved': True, 'caller_must_save_package': False, 'runtime_tested': False})
report.update({'stage': 'V13 model, cloth, LODs and physics saved; clips and BP pending',
               'mesh': path(mesh), 'skeleton': path(skeleton), 'body_physics': physics, 'cloth': cloth})
receipt()
clips = {}
for role, entry in motion['clips'].items():
    clip = import_file(entry['file'], 'A_M07_'+role, ANIM, skeleton, animation=True)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'OriginalV13 minimum-twist leg orientation and reauthored attacks; unchanged V11 reference')
    LIB.set_metadata_tag(clip, 'MotionSourceManifest', str(MANIFEST))
    save(clip)
    clips[role] = clip
defaults.set_editor_property('visual_mesh', mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
clip_props = {'idle_clip': 'Idle', 'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase', 'walk_clip': 'Chase',
              'attack_clip': 'MeleeLeft', 'melee_left_clip': 'MeleeLeft', 'melee_right_clip': 'MeleeRight',
              'death_clip': 'Death', 'wall_listen_clip': 'WallListen'}
for prop, role in clip_props.items():
    report['previous_clip_references'][prop] = path(defaults.get_editor_property(prop))
    defaults.set_editor_property(prop, clips[role])
combat = defaults.get_editor_property('combat')
knockdown = defaults.get_editor_property('knockdown')
for prop, role in {'hit_clip': 'Hit', 'dizzy_clip': 'Dizzy'}.items():
    combat.set_editor_property(prop, clips[role])
for prop, role in {'fall_clip': 'Fall', 'get_up_clip': 'GetUp', 'prone_get_up_clip': 'ProneGetUp'}.items():
    knockdown.set_editor_property(prop, clips[role])
speeds = {'walk_speed': 160., 'chase_speed': 360., 'source_walk_speed': 160., 'source_chase_speed': 360.}
for prop, value in {**speeds, 'cloth_resume_distance': 1000., 'cloth_suspend_distance': 1400.}.items():
    defaults.set_editor_property(prop, value)
defaults.get_editor_property('character_movement').set_editor_property('max_walk_speed', 360.)
LIB.set_metadata_tag(bp, 'SourceRevision', 'OriginalV13 local skin, minimum-twist actions, bounded lower-cost cloth and distance LODs; user review pending')
LIB.set_metadata_tag(bp, 'MotionSourceManifest', str(MANIFEST))
LIB.set_metadata_tag(bp, 'LocomotionRevision', 'OriginalV13 minimum leg roll; larger 160/360cm/s coordinated locomotion; user review pending')
LIB.set_metadata_tag(bp, 'LocomotionSourceManifest', str(MANIFEST))
LIB.set_metadata_tag(bp, 'ArmGillCollisionManifest', str(CLOTH_MANIFEST))
save(bp)
report.update({'saved': True, 'stage': 'V13 model, cloth, 3 LODs, physics, twelve actions and AI/F6 Blueprint saved',
               'blueprint': path(bp), 'ai_and_f6_preserved': True, 'speeds_cm_s': speeds,
               'cloth_distance_cm': {'resume': 1000., 'suspend': 1400.},
               'clips': {role: {'asset': path(clip), 'duration_s': clip.get_play_length(), 'source': motion['clips'][role]['file']}
                         for role, clip in clips.items()}})
receipt()
for filename in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT/filename
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update({'revision': 'OriginalV13', 'geometry_revision': 'OriginalV13 original body retained; original leaves reduced',
        'stage': report['stage'], 'mesh': report['mesh'], 'skeleton': report['skeleton'],
        'ue_save_receipt': str(REPORT), 'motion_authoring_receipt': str(MANIFEST),
        'active_animation_source': motion['source'], 'active_cloth_collision_source': str(CLOTH_MANIFEST),
        'body_physics': physics, 'interacting_gills': cloth, 'speeds_cm_s': speeds,
        'original_recovery_v13_saved': True, 'animation_stage': 'Twelve OriginalV13 reference-consistent actions saved',
        'user_review_pending': True, 'user_accepted_model': False, 'user_accepted_motion': False,
        'runtime_tested': False, 'visual_tested': False, 'tested': False})
    for asset in report['assets']:
        if asset not in record.setdefault('assets', []):
            record['assets'].append(asset)
    if filename == 'gameplay_delivery.json':
        record.setdefault('character_blueprint', {}).update({'mesh': report['mesh'],
            'clip_properties': {prop: path(clips[role]) for prop, role in clip_props.items()}})
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V13_ORIGINAL_RECOVERY_ASSETS_AND_AI_F6_SAVED '+str(REPORT), flush=True)
