"""Save M07 four combat clips and the existing AI/F6 Blueprint, without PIE."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'CombatMagicV14'
MANIFEST = OUT/'Motion/motion_manifest_v14.json'
REPORT = OUT/'ue_combat_magic_delivery_v14.json'
DEST = '/Game/Monsters/BlindSupplicantM07'
ANIM = DEST+'/AnimationsCombatMagicV14'
BP = DEST+'/BP_BlindSupplicantM07'
ROLES = ('SweepLeft', 'SweepRight', 'MagicGather', 'MagicRelease')
SAVE_PATHS = {BP, *(ANIM+'/A_M07_'+role for role in ROLES)}
OUT.mkdir(parents=True, exist_ok=True)
LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('M07 V14 production belongs to FPSGAME.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Existing PIE preserved; M07 V14 saving deferred.')
motion = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
report = {'revision': 'CombatMagicV14', 'saved': False, 'assets': [],
          'motion_manifest': str(MANIFEST), 'model_reimported': False,
          'geometry_revision_retained': 'OriginalV13', 'tested': False,
          'runtime_tested': False, 'visual_tested': False, 'user_review_pending': True,
          'native_editor_and_game_built': False}


def receipt():
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


def save(asset):
    if not asset or asset.get_path_name().split('.', 1)[0] not in SAVE_PATHS:
        raise RuntimeError('M07 V14 saving is outside the four clips and existing Blueprint.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 V14 package did not save: '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())
    receipt()


skeleton = u.load_asset(DEST+'/SK_M07_ReferenceOriginalV11')
mesh = u.load_asset(DEST+'/SK_M07_OriginalV13')
bp = u.load_asset(BP)
if not skeleton or not mesh or not bp:
    raise RuntimeError('Existing M07 V13 model, V11 reference and AI/F6 Blueprint required.')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
report['previous_visual_mesh'] = defaults.get_editor_property('visual_mesh').get_path_name()
receipt()
clips = {}
for role in ROLES:
    entry = motion['clips'][role]
    file = Path(entry['file'])
    if not file.is_file() or not file.resolve().is_relative_to((OUT/'Motion').resolve()):
        raise RuntimeError('M07 V14 export absent or outside its motion production directory: '+str(file))
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
    data = options.anim_sequence_import_data
    data.convert_scene = True
    data.convert_scene_unit = True
    data.import_uniform_scale = 1.
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', int(entry.get('fps', motion.get('fps', 30))))
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = ANIM
    task.destination_name = 'A_M07_'+role
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.factory = u.FbxFactory()
    AT.import_asset_tasks([task])
    clip = u.load_asset(ANIM+'/A_M07_'+role)
    if not clip or not task.imported_object_paths or clip.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('M07 V14 animation did not import with its unchanged reference: '+role)
    clip.set_preview_skeletal_mesh(mesh)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_editor_property('enable_root_motion', False)
    LIB.set_metadata_tag(clip, 'CombatMagicSource', str(MANIFEST))
    LIB.set_metadata_tag(clip, 'SourceRevision', 'M07 CombatMagicV14; HundredEyed sweep reference, player gather/release reference; user review pending')
    save(clip)
    clips[role] = clip
properties = {'melee_left_clip': 'SweepLeft', 'melee_right_clip': 'SweepRight', 'attack_clip': 'SweepLeft',
              'magic_gather_clip': 'MagicGather', 'magic_release_clip': 'MagicRelease'}
for prop, role in properties.items():
    defaults.set_editor_property(prop, clips[role])
left = motion['clips']['SweepLeft']
right = motion['clips']['SweepRight']
values = {'left_contact_time': left.get('contact_seconds', left.get('impact_seconds', .68)),
          'right_contact_time': right.get('contact_seconds', right.get('impact_seconds', .78)),
          'contact_window_seconds': .16, 'magic_attack': 40.,
          'fireball_damage_multiplier': 1.6, 'ice_column_damage_multiplier': 1.4,
          'lightning_damage_multiplier': 1.5, 'fireball_cooldown': 8.,
          'ice_column_cooldown': 10., 'lightning_cooldown': 12.,
          'fireball_range': 1400., 'ice_column_range': 1500., 'lightning_range': 1200.,
          'fireball_speed': 1500., 'ice_column_speed': 2000.,
          'fireball_impact_radius': 140., 'ice_column_impact_radius': 24.,
          'magic_minimum_distance': 240., 'sweep_hit_radius': 35.,
          'magic_release_contact_time': motion['clips']['MagicRelease'].get('contact_seconds', .30),
          'magic_attacks_enabled': True}
for prop, value in values.items():
    defaults.set_editor_property(prop, value)
LIB.set_metadata_tag(bp, 'CombatMagicRevision', 'CombatMagicV14; bilateral sweeps and three independently cooled two-phase spells; original V13 model retained')
LIB.set_metadata_tag(bp, 'CombatMagicSource', str(MANIFEST))
save(bp)
report.update({'saved': True, 'stage': 'Four V14 clips, default magic numbers and existing AI/F6 Blueprint saved',
               'blueprint': bp.get_path_name(), 'mesh': mesh.get_path_name(), 'skeleton': skeleton.get_path_name(),
               'ai_and_f6_preserved': True, 'default_properties': values,
               'clips': {role: dict(motion['clips'][role], asset=clip.get_path_name(), duration_s=clip.get_play_length())
                         for role, clip in clips.items()}})
receipt()
for name in ('production_status.json', 'gameplay_delivery.json'):
    p = ROOT/name
    record = json.loads(p.read_text(encoding='utf-8-sig'))
    record.update({'revision': 'CombatMagicV14', 'geometry_revision': 'OriginalV13 retained',
        'stage': report['stage'], 'ue_save_receipt': str(REPORT), 'combat_magic_v14_saved': True,
        'combat_magic_source': str(MANIFEST), 'combat_magic_defaults': values,
        'native_editor_and_game_built': False,
        'user_review_pending': True, 'runtime_tested': False, 'visual_tested': False, 'tested': False})
    for asset in report['assets']:
        if asset not in record.setdefault('assets', []):
            record['assets'].append(asset)
    p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_V14_SWEEP_MAGIC_CLIPS_AND_AI_F6_SAVED '+str(REPORT), flush=True)
