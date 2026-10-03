"""Produce and save M07 local arm skin and two forceful sweeps, without gameplay."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'ArmSweepV16'
SKIN = OUT/'Skin/skin_manifest_v16.json'
MOTION = OUT/'Motion/power_sweep_manifest_v16.json'
REPORT = OUT/'ue_arm_sweep_delivery_v16.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
MESH = DEST+'/SK_M07_ArmSweepV16'
ANIM = DEST+'/AnimationsArmSweepV16'
BP = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SweepLeft', 'SweepRight')
SAVE_PATHS = {MESH, BP, *(ANIM+'/A_M07_'+r for r in ROLES)}
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
OUT.mkdir(parents=True, exist_ok=True)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V16 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not level_editor:
        raise RuntimeError('Current bridge is not an asset-editing editor context; M07 V16 packages preserved.')
    if level_editor.is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; M07 V16 saving deferred.')
skin = json.loads(SKIN.read_text(encoding='utf-8-sig'))
motion = json.loads(MOTION.read_text(encoding='utf-8-sig'))
report = {'revision':'ArmSweepV16', 'saved':False, 'assets':[],
          'skin_manifest':str(SKIN), 'motion_manifest':str(MOTION),
          'original_geometry_uv_retained':True, 'reference_pose_changed':False,
          'native_editor_and_game_built':False, 'tested':False, 'runtime_tested':False,
          'visual_tested':False, 'user_review_pending':True}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def path(asset):
    return asset.get_path_name() if asset else None


def save(asset):
    if not asset or path(asset).split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V16 save outside candidate mesh, two sweeps and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V16 asset did not save: '+path(asset))
    if path(asset) not in report['assets']:
        report['assets'].append(path(asset))
    receipt()


def import_file(filename, name, destination, skeleton, animation=False):
    filename = Path(filename)
    if not filename.is_file() or not filename.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError('M07 V16 export absent or outside production directory: '+str(filename))
    value = u.FbxImportUI()
    value.automated_import_should_detect_type = False
    value.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    value.import_as_skeletal = True
    value.import_mesh = not animation
    value.import_animations = animation
    value.import_materials = value.import_textures = value.create_physics_asset = False
    value.skeleton = skeleton
    data = value.anim_sequence_import_data if animation else value.skeletal_mesh_import_data
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
    task.options = value
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination+'/'+name)
    if not asset or not task.imported_object_paths or asset.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V16 import did not reuse the original reference: '+name)
    return asset


skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
simulation = u.load_asset(DEST+'/Working/SK_M07_ClothBuildSource_OriginalV13')
physics = u.load_asset(DEST+'/PA_M07_OriginalV13')
bp = u.load_asset(BP)
materials = {'M07_Body':u.load_asset(DEST+'/Materials/M07_Body_OriginalV07'),
             'M07_Gills':u.load_asset(DEST+'/Materials/M07_Gills_OriginalV07')}
if not skeleton or not simulation or not physics or not bp or not all(materials.values()):
    raise RuntimeError('Existing V11 reference, V13 cloth source/physics, materials and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
defaults.get_editor_property('melee_playback_rate')  # Requires this revision's reflected native field before importing.
report['previous_visual_mesh'] = path(defaults.get_editor_property('visual_mesh'))
retained = {prop:path(defaults.get_editor_property(prop)) for prop in
            ('slow_walk_clip','chase_clip','walk_clip','death_clip','magic_gather_clip','magic_release_clip')}
receipt()
existing = u.load_asset(MESH)
if existing:
    u.BlindSupplicantAuthoring.remove_gill_cloth_for_reimport(existing)
mesh = import_file(skin['display_fbx'], 'SK_M07_ArmSweepV16', DEST, skeleton)
slots = list(mesh.materials)
for slot in slots:
    name = str(slot.get_editor_property('imported_material_slot_name'))
    name = 'M07_Body' if name == 'M07_Identity' else name
    if name not in materials:
        raise RuntimeError('Unassigned original-UV material slot: '+name)
    slot.material_interface = materials[name]
mesh.set_editor_property('materials', slots)
mesh.set_editor_property('physics_asset', physics)
cloth_manifest = ROOT/'RecoveryOriginalV13/cloth_ue_manifest_original_v13.json'
cloth = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(mesh, simulation, str(cloth_manifest)))
if not cloth.get('success'):
    raise RuntimeError('M07 V16 original gill cloth could not bind: '+json.dumps(cloth))
if not u.BlindSupplicantAuthoring.configure_distance_lods(mesh):
    raise RuntimeError('M07 V16 original distance LOD recipe could not apply.')
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not editor.regenerate_lod(mesh, 3, False, False):
    raise RuntimeError('M07 V16 candidate distance LOD generation did not complete.')
LIB.set_metadata_tag(mesh, 'ArmSkinRevision', 'ArmSweepV16 local anatomical surface skin; original geometry/UV/legs/fingers/reference retained; user review pending')
LIB.set_metadata_tag(mesh, 'ArmSkinSourceManifest', str(SKIN))
LIB.set_metadata_tag(mesh, 'ArmGillCollisionManifest', str(cloth_manifest))
save(mesh)
cloth.update({'saved':True, 'caller_must_save_package':False, 'runtime_tested':False})
report.update({'mesh':path(mesh), 'skeleton':path(skeleton), 'physics_asset':path(physics),
               'reused_cloth_simulation':path(simulation), 'cloth':cloth,
               'generated_lods':[{'lod':i, 'vertices':editor.get_num_verts(mesh, i),
                                  'sections':editor.get_num_sections(mesh, i)} for i in range(editor.get_lod_count(mesh))]})
receipt()
clips = {}
for role in ROLES:
    entry = motion['clips'][role]
    clip = import_file(entry['file'], 'A_M07_'+role, ANIM, skeleton, True)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'SourceRevision', 'ArmSweepV16 HundredEyed weight shift, hip/chest/shoulder lead, accelerated cross and follow-through')
    save(clip)
    clips[role] = clip
defaults.set_editor_property('visual_mesh', mesh)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
defaults.set_editor_property('melee_left_clip', clips['SweepLeft'])
defaults.set_editor_property('melee_right_clip', clips['SweepRight'])
defaults.set_editor_property('attack_clip', clips['SweepLeft'])
rate = 1.30
values = {'melee_playback_rate':rate,
          'left_contact_time':float(motion['clips']['SweepLeft']['contact_seconds']),
          'right_contact_time':float(motion['clips']['SweepRight']['contact_seconds']),
          'contact_window_seconds':float(motion['clips']['SweepLeft']['contact_window_seconds'])}
for prop, value in values.items():
    defaults.set_editor_property(prop, value)
LIB.set_metadata_tag(bp, 'ArmSweepRevision', 'ArmSweepV16 local arm skin and faster powered sweep; V15 movement/death/casting/CD and AI/F6 retained')
LIB.set_metadata_tag(bp, 'ArmSkinSourceManifest', str(SKIN))
LIB.set_metadata_tag(bp, 'ArmGillCollisionManifest', str(cloth_manifest))
save(bp)
report.update({'saved':True, 'stage':'Local arm skin, original cloth/LOD, two powered sweeps and existing AI/F6 saved',
               'blueprint':path(bp), 'ai_and_f6_preserved':True, 'default_properties':values,
               'v15_references_retained':retained,
               'clips':{role:{'asset':path(clip), 'source':motion['clips'][role]['file'],
                               'duration_s':clip.get_play_length(),
                               'runtime_duration_s':clip.get_play_length()/rate,
                               'contact_clip_s':motion['clips'][role]['contact_seconds'],
                               'contact_runtime_s':motion['clips'][role]['contact_seconds']/rate}
                        for role, clip in clips.items()}})
receipt()
for name in ('production_status.json','gameplay_delivery.json'):
    p = ROOT/name
    record = json.loads(p.read_text(encoding='utf-8-sig'))
    record.update({'revision':'ArmSweepV16', 'geometry_revision':'OriginalV13 preserved; local V16 arm weights',
                   'stage':report['stage'], 'mesh':report['mesh'], 'ue_save_receipt':str(REPORT),
                   'arm_sweep_v16_saved':True, 'arm_sweep_v16_defaults':values,
                   'native_editor_and_game_built':False, 'runtime_tested':False,
                   'visual_tested':False, 'tested':False, 'user_review_pending':True})
    for asset in report['assets']:
        if asset not in record.setdefault('assets',[]):
            record['assets'].append(asset)
    p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V16_LOCAL_ARM_SKIN_POWERED_SWEEPS_AND_AI_F6_SAVED '+str(REPORT), flush=True)
