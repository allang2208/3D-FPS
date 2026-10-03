"""Save original M07 contact layers and four full-body clips to the existing AI/F6."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'BodyMotionV18'
PROXY = OUT / 'Proxy/proxy_manifest_v18.json'
ATTACK = OUT / 'Attack/body_sweep_manifest_v18.json'
MOVE = OUT / 'Move/body_gait_manifest_v18.json'
REPORT = OUT / 'ue_body_motion_delivery_v18.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
MESH = DEST + '/SK_M07_BodyMotionV18'
SIM = DEST + '/Working/SK_M07_ClothBuildSource_BodyMotionV18'
ANIM = DEST + '/AnimationsBodyMotionV18'
BP = DEST + '/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase', 'SweepLeft', 'SweepRight')
SAVE_PATHS = {MESH, SIM, BP, *(ANIM + '/A_M07_' + role for role in ROLES)}
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
OUT.mkdir(parents=True, exist_ok=True)

if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT / 'FPSGAME.uproject':
    raise RuntimeError('M07 V18 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not level_editor or level_editor.is_in_play_in_editor():
        raise RuntimeError('Existing non-editing/PIE context preserved; M07 V18 saving deferred.')

proxy = json.loads(PROXY.read_text(encoding='utf-8-sig'))
attack = json.loads(ATTACK.read_text(encoding='utf-8-sig'))
move = json.loads(MOVE.read_text(encoding='utf-8-sig'))
entries = {**move['clips'], **attack['clips']}
report = {'revision': 'BodyMotionV18', 'saved': False, 'assets': [],
          'manifests': [str(PROXY), str(ATTACK), str(MOVE)],
          'original_geometry_uv_retained': True, 'reference_pose_changed': False,
          'leg_skin_revision_retained': 'LegJointsV17', 'arm_skin_revision_retained': 'ArmSweepV16',
          'death_casting_cooldown_revision_retained': 'MotionRecoveryV15',
          'native_editor_and_game_built': False, 'tested': False,
          'runtime_tested': False, 'visual_tested': False, 'user_review_pending': True}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def path(asset):
    return asset.get_path_name() if asset else None


def save(asset):
    if not asset or path(asset).split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V18 save outside original candidate mesh/proxy/four clips/existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V18 package did not save: ' + path(asset))
    if path(asset) not in report['assets']:
        report['assets'].append(path(asset))
    receipt()


def import_file(filename, name, destination, skeleton, animation=False):
    filename = Path(filename)
    if not filename.is_file() or not filename.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError('M07 V18 export absent or outside production directory: ' + str(filename))
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = not animation
    options.import_animations = animation
    options.import_materials = options.import_textures = options.create_physics_asset = False
    options.skeleton = skeleton
    data = options.anim_sequence_import_data if animation else options.skeletal_mesh_import_data
    data.convert_scene = data.convert_scene_unit = True
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
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_name = name
    task.destination_path = destination
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination + '/' + name)
    if not asset or not task.imported_object_paths or asset.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V18 import did not reuse original reference: ' + name)
    return asset


skeleton = u.load_asset(DEST + '/SK_M07_ReferenceOriginalV11')
physics = u.load_asset(DEST + '/PA_M07_OriginalV13')
bp = u.load_asset(BP)
materials = {'M07_Body': u.load_asset(DEST + '/Materials/M07_Body_OriginalV07'),
             'M07_Gills': u.load_asset(DEST + '/Materials/M07_Gills_OriginalV07')}
if not skeleton or not physics or not bp or not all(materials.values()):
    raise RuntimeError('Existing V11 reference, V13 body physics, original materials and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
report['previous_visual_mesh'] = path(defaults.get_editor_property('visual_mesh'))
report['retained_references'] = {prop: path(defaults.get_editor_property(prop)) for prop in (
    'idle_clip', 'death_clip', 'magic_gather_clip', 'magic_release_clip', 'wall_listen_clip')}
receipt()

simulation = import_file(proxy['simulation_fbx'], 'SK_M07_ClothBuildSource_BodyMotionV18', DEST + '/Working', skeleton)
simulation_slots = list(simulation.materials)
for slot in simulation_slots:
    slot.material_interface = materials['M07_Gills']
simulation.set_editor_property('materials', simulation_slots)
simulation.set_editor_property('physics_asset', physics)
save(simulation)
existing = u.load_asset(MESH)
if existing:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing)
mesh = import_file(proxy['display_fbx'], 'SK_M07_BodyMotionV18', DEST, skeleton)
slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    name = 'M07_Body' if name == 'M07_Identity' else name
    if name not in materials:
        raise RuntimeError('Unassigned original-UV material slot: ' + name)
    slot.material_interface = materials[name]
mesh.set_editor_property('materials', slots)
mesh.set_editor_property('physics_asset', physics)
cloth_manifest = Path(proxy['cloth_manifest'])
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(mesh, simulation, str(cloth_manifest)))
if not cloth.get('success'):
    raise RuntimeError('M07 V18 local-contact gill cloth could not bind: ' + json.dumps(cloth))
if not u.BlindSupplicantAuthoring.configure_distance_lods(mesh):
    raise RuntimeError('M07 V18 original distance LOD recipe could not apply.')
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not editor.regenerate_lod(mesh, 3, False, False):
    raise RuntimeError('M07 V18 candidate LOD generation did not complete.')
LIB.set_metadata_tag(mesh, 'BodyMotionRevision', 'V18 original body/UV/V16 arms/V17 legs, local gill contact proxy; user review pending')
LIB.set_metadata_tag(mesh, 'GillContactSourceManifest', str(PROXY))
save(mesh)
report.update(mesh=path(mesh), skeleton=path(skeleton), physics_asset=path(physics),
              simulation_source=path(simulation), cloth=cloth,
              generated_lods=[{'lod': i, 'vertices': editor.get_num_verts(mesh, i),
                               'sections': editor.get_num_sections(mesh, i)} for i in range(editor.get_lod_count(mesh))])
receipt()

clips = {}
for role in ROLES:
    entry = entries[role]
    clip = import_file(entry['file'], 'A_M07_' + role, ANIM, skeleton, True)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'BodyMotionRevision', 'V18 full-body gait or quiet-opposite-arm committed sweep; user review pending')
    save(clip)
    clips[role] = clip

defaults.set_editor_property('visual_mesh', mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
for prop, role in {'slow_walk_clip': 'SlowWalk', 'chase_clip': 'Chase', 'walk_clip': 'Chase',
                   'melee_left_clip': 'SweepLeft', 'melee_right_clip': 'SweepRight', 'attack_clip': 'SweepLeft'}.items():
    defaults.set_editor_property(prop, clips[role])
defaults.set_editor_property('left_contact_time', float(entries['SweepLeft']['contact_time']))
defaults.set_editor_property('right_contact_time', float(entries['SweepRight']['contact_time']))
defaults.set_editor_property('contact_window_seconds', .12)
defaults.set_editor_property('melee_playback_rate', 1.30)
defaults.set_editor_property('cloth_resume_distance', 650.)
defaults.set_editor_property('cloth_suspend_distance', 850.)
defaults.set_editor_property('enable_gill_bone_clearance', True)
defaults.set_editor_property('gill_clearance_angle_degrees', 18.)
LIB.set_metadata_tag(bp, 'BodyMotionRevision', 'V18 committed sweeps, full-body gait, bounded gill contacts; original AI/F6 and V15 magic/death retained')
LIB.set_metadata_tag(bp, 'BodyMotionSourceManifests', ';'.join(report['manifests']))
save(bp)
report.update(saved=True, stage='Original model, gill proxy/cloth, four full-body clips and existing AI/F6 saved',
              blueprint=path(bp), ai_and_f6_preserved=True,
              cloth_budget={'capsules': cloth.get('collision_capsules'), 'iterations': cloth.get('solver_iterations'),
                            'substeps': cloth.get('solver_substeps'), 'resume_cm': 650., 'suspend_cm': 850.,
                            'bone_clearance_leaves': 6, 'per_evaluation_segment_checks': 72},
              clips={role: dict(entries[role], asset=path(clip), duration_s=clip.get_play_length())
                     for role, clip in clips.items()})
receipt()
for name in ('production_status.json', 'gameplay_delivery.json'):
    record_path = ROOT / name
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    record.update(revision='BodyMotionV18', geometry_revision='Original surface/UV/skin with V16 arm and V17 leg weights retained; new local-contact simulation proxy',
                  stage=report['stage'], mesh=report['mesh'], ue_save_receipt=str(REPORT),
                  body_motion_v18_saved=True, body_motion_v18_manifests=report['manifests'],
                  native_editor_and_game_built=False, runtime_tested=False,
                  visual_tested=False, tested=False, user_review_pending=True)
    for asset in report['assets']:
        if asset not in record.setdefault('assets', []): record['assets'].append(asset)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('M07_V18_BODY_MOTION_GILL_CONTACT_AND_AI_F6_SAVED ' + str(REPORT), flush=True)
