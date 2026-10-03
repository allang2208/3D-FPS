"""Save five M07 motion repairs and formal-skill cooldowns; no gameplay."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'MotionRecoveryV15'
MANIFESTS = (OUT/'LocomotionDeath/motion_manifest_v15.json', OUT/'Casting/casting_manifest_v15.json')
REPORT = OUT/'ue_motion_recovery_delivery_v15.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsMotionRecoveryV15'
BP = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SlowWalk', 'Chase', 'Death', 'MagicGather', 'MagicRelease')
SAVE_PATHS = {BP, *(ANIM+'/A_M07_'+role for role in ROLES)}
OUT.mkdir(parents=True, exist_ok=True)
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V15 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; M07 V15 saving deferred.')
motion = {}
for path in MANIFESTS:
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    motion.update(manifest['clips'])
skills = json.loads((PROJECT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))
report = {'revision': 'MotionRecoveryV15', 'saved': False, 'assets': [],
          'motion_manifests': [str(p) for p in MANIFESTS], 'model_reimported': False,
          'geometry_revision_retained': 'OriginalV13', 'sweep_revision_retained': 'CombatMagicV14',
          'native_editor_and_game_built': False, 'runtime_tested': False,
          'visual_tested': False, 'user_review_pending': True, 'tested': False}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not asset or asset.get_path_name().split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V15 save is outside the five motions and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V15 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()


skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
mesh = u.load_asset(DEST+'/SK_M07_OriginalV13')
bp = u.load_asset(BP)
if not skeleton or not mesh or not bp:
    raise RuntimeError('Existing M07 V13 body, V11 reference and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
report['previous_visual_mesh'] = defaults.get_editor_property('visual_mesh').get_path_name()
receipt()
clips = {}
for role in ROLES:
    entry = motion[role]
    file = Path(entry['file'])
    if not file.is_file() or not file.resolve().is_relative_to(OUT.resolve()):
        raise RuntimeError('M07 V15 export absent or outside its motion production directory: '+str(file))
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
    data.set_editor_property('custom_sample_rate', int(entry.get('fps', 30)))
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = ANIM
    task.destination_name = 'A_M07_'+role
    task.automated = True
    task.save = False
    task.replace_existing = task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    clip = u.load_asset(ANIM+'/A_M07_'+role)
    if not clip or not task.imported_object_paths or clip.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V15 animation not imported with the original reference: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'MotionRecoveryRevision', 'M07 V15: anatomical gathering/push, whole-body locomotion, grounded fall; user review pending')
    save(clip)
    clips[role] = clip
for prop, role in {'slow_walk_clip':'SlowWalk', 'chase_clip':'Chase', 'walk_clip':'Chase',
                   'death_clip':'Death', 'magic_gather_clip':'MagicGather', 'magic_release_clip':'MagicRelease'}.items():
    defaults.set_editor_property(prop, clips[role])
values = {'fireball_cooldown': float(skills['fireball']['cooldown']),
          'ice_column_cooldown': float(skills['iceSpike']['cooldown']),
          'lightning_cooldown': float(skills['lightningStrike']['cooldown']),
          'use_player_skill_cooldowns': True,
          'magic_release_contact_time': float(motion['MagicRelease'].get('contact_seconds', .30)),
          'source_walk_speed':160., 'source_chase_speed':360., 'walk_speed':160., 'chase_speed':360.}
for prop, value in values.items():
    defaults.set_editor_property(prop, value)
LIB.set_metadata_tag(bp, 'MotionRecoveryRevision', 'MotionRecoveryV15; formal level-one skill CD with shared magic interval and uncommitted refund; original V13 body and V14 sweeps retained')
save(bp)
report.update({'saved': True, 'stage': 'Five V15 motions and formal-skill cooldowns saved to existing AI/F6 Blueprint',
               'blueprint':bp.get_path_name(), 'mesh':mesh.get_path_name(), 'skeleton':skeleton.get_path_name(),
               'ai_and_f6_preserved':True, 'default_properties':values,
               'cooldown_source':str(PROJECT/'Content/ColdSteelData/skills.json'),
               'cooldown_contract':'Start at gathering; shared interval prevents element cycling; uncommitted interruption refunds',
               'death_handoff_fraction':.6,
               'clips':{role:dict(motion[role], asset=clip.get_path_name(), duration_s=clip.get_play_length())
                        for role, clip in clips.items()}})
receipt()
for name in ('production_status.json','gameplay_delivery.json'):
    p = ROOT/name
    record = json.loads(p.read_text(encoding='utf-8-sig'))
    record.update({'revision':'MotionRecoveryV15', 'geometry_revision':'OriginalV13 retained',
        'stage':report['stage'], 'ue_save_receipt':str(REPORT), 'motion_recovery_v15_saved':True,
        'motion_recovery_source':[str(p) for p in MANIFESTS], 'motion_recovery_defaults':values,
        'native_editor_and_game_built':False, 'runtime_tested':False, 'visual_tested':False,
        'tested':False, 'user_review_pending':True})
    for asset in report['assets']:
        if asset not in record.setdefault('assets',[]): record['assets'].append(asset)
    p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V15_FIVE_MOTIONS_FORMAL_SKILL_CD_AND_AI_F6_SAVED '+str(REPORT), flush=True)
