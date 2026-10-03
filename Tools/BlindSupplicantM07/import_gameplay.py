"""Produce and save M07 body actions, collision, character BP and map navigation.

No gameplay spawn, BeginPlay, PIE, path probe, rendering or automated tests.
"""
import json
import runpy
import shutil
from pathlib import Path

import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
TOOLS = Path('D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07')
DEST = '/Game/Monsters/BlindSupplicantM07'
BP_PATH = DEST + '/BP_BlindSupplicantM07'
REPORT = ROOT / 'gameplay_delivery.json'
MAP = '/Game/GameMaps/DayNight_Lighting'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != ROOT.parent.parent/'FPSGAME.uproject':
    raise RuntimeError('M07 gameplay production belongs to the FPSGAME host.')
if not hasattr(u, 'BlindSupplicantMonster'):
    raise RuntimeError('Complete the native M07 Editor build before importing gameplay assets.')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('M07 gameplay package authoring must finish outside PIE.')

LIB = u.EditorAssetLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
report = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'completed': [], 'assets': []}
report.update({'runtime_tested': False, 'visual_tested': False, 'execution_mode': globals().get('M07_EXECUTION_MODE', 'background_commandlet')})


class M07GameplaySavedStage(Exception):
    pass


def record(stage, receipt=None):
    if stage not in report['completed']:
        report['completed'].append(stage)
    if receipt is not None:
        report[stage] = receipt
    report['stage'] = 'saved_' + stage
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07 GAMEPLAY SAVED ' + stage, flush=True)
    if globals().get('M07_GAMEPLAY_STOP_AFTER') == stage:
        raise M07GameplaySavedStage(stage)


def save(asset):
    if not asset or not asset.get_path_name().startswith(DEST + '/'):
        raise RuntimeError('Gameplay asset is outside M07 ownership.')
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('M07 gameplay package could not be saved: ' + asset.get_path_name())
    if asset.get_path_name() not in report['assets']:
        report['assets'].append(asset.get_path_name())


def import_file(filename, name, destination, options=None, factory=None):
    if not filename.is_file():
        raise RuntimeError('Required M07 production source is missing: ' + str(filename))
    task = u.AssetImportTask()
    task.filename = str(filename)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    if options is not None:
        task.options = options
    if factory is not None:
        task.factory = factory
    AT.import_asset_tasks([task])
    asset = u.load_asset(destination + '/' + name)
    if not asset or not task.imported_object_paths:
        raise RuntimeError('M07 source import did not produce an asset: ' + str(filename))
    return asset


def animation_options(skeleton, sample_rate=30):
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
    data.import_uniform_scale = 1.0
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', sample_rate)
    data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    data.set_editor_property('preserve_local_transform', True)
    return options


mesh = u.load_asset(DEST + '/SK_M07')
if not mesh:
    raise RuntimeError('Save the M07 display mesh and original cloth before gameplay production.')
clips = {}
CLIP_NAMES = ('Idle', 'SlowWalk', 'Chase', 'MeleeLeft', 'MeleeRight', 'Hit', 'Death', 'WallListen',
              'Dizzy', 'Fall', 'GetUp', 'ProneGetUp')
if 'animations' not in report['completed']:
    imported = []
    for name in CLIP_NAMES:
        filename = ROOT / 'Motion' / ('A_M07_' + name + '.fbx')
        clip = import_file(filename, 'A_M07_' + name, DEST + '/Animations',
                           animation_options(mesh.skeleton), u.FbxFactory())
        clip.set_preview_skeletal_mesh(mesh)
        LIB.set_metadata_tag(clip, 'Production', 'M07 whole-body action with six phase-offset gill chains; user runtime review pending')
        save(clip)
        clips[name] = clip
        imported.append({'name': name, 'source': str(filename), 'asset': clip.get_path_name(), 'duration_s': clip.get_play_length()})
    save(mesh.skeleton)
    record('animations', {'saved': True, 'clips': imported})
else:
    clips = {name: u.load_asset(DEST + '/Animations/A_M07_' + name) for name in CLIP_NAMES}

if 'body_physics' not in report['completed']:
    author_physics = runpy.run_path(str(TOOLS/'author_physics.py'), run_name='m07_physics_production')
    physics = author_physics['author_and_save']()
    if physics['physics_asset'] not in report['assets']:
        report['assets'].append(physics['physics_asset'])
    record('body_physics', physics)

if 'interacting_gills' not in report['completed']:
    before = ROOT/'Authoring'/'BeforeInteractingGills'
    before.mkdir(exist_ok=True)
    source_package = ROOT.parent.parent/'Content/Monsters/BlindSupplicantM07/SK_M07.uasset'
    backup = before/'SK_M07.uasset'
    if not backup.exists():
        shutil.copy2(source_package, backup)
    manifest = str(ROOT/'Authoring/cloth_ue_manifest.json')
    # A separate preserved source restores the original six physical islands
    # without replacing a display package that an existing editor may hold.
    working = ROOT.parent.parent/'Content/Monsters/BlindSupplicantM07/Working'
    working.mkdir(exist_ok=True)
    simulation_package = working/'SK_M07_OriginalSix_20261001.uasset'
    if not simulation_package.exists():
        shutil.copy2(backup, simulation_package)
    simulation_source = u.load_object(None, DEST + '/Working/SK_M07_OriginalSix_20261001.SK_M07')
    if not simulation_source:
        raise RuntimeError('The preserved M07 six-panel physical source could not be loaded.')
    receipt = json.loads(u.BlindSupplicantAuthoring.build_interacting_gill_cloth_from_saved_source(mesh, simulation_source, manifest))
    if not receipt.get('success'):
        raise RuntimeError('M07 interacting gill production failed: ' + json.dumps(receipt, ensure_ascii=False))
    LIB.set_metadata_tag(mesh, 'Cloth', 'Six separate visible gill panels with six disconnected proxy islands in one Chaos self-collision particle set')
    save(mesh)
    receipt['saved'] = True
    receipt['caller_must_save_package'] = False
    (ROOT/'Authoring/interacting_gills_delivery.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    record('interacting_gills', receipt)

if 'audio' not in report['completed']:
    mimic = import_file(ROOT/'Audio/SC_M07_WallMimic.wav', 'SW_M07_WallMimic', DEST+'/Audio', factory=u.SoundFactory())
    LIB.set_metadata_tag(mimic, 'Source', 'Local offline Microsoft Huihui speech; temporary internal prototype wall mimic; not final actor performance')
    save(mimic)
    record('audio', {'saved': True, 'asset': mimic.get_path_name(), 'temporary_internal_test_voice': True})
else:
    mimic = u.load_asset(DEST+'/Audio/SW_M07_WallMimic')

if 'character_blueprint' not in report['completed']:
    bp = u.load_asset(BP_PATH)
    if not bp:
        factory = u.BlueprintFactory()
        factory.set_editor_property('parent_class', u.BlindSupplicantMonster)
        bp = AT.create_asset('BP_BlindSupplicantM07', DEST, u.Blueprint, factory)
    if not bp:
        raise RuntimeError('M07 character Blueprint was not produced.')
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults = u.get_default_object(bp.generated_class())
    defaults.set_editor_property('visual_mesh', mesh)
    body = defaults.get_editor_property('mesh')
    body.set_skeletal_mesh_asset(mesh)
    body.set_anim_instance_class(u.BlindSupplicantAnimInstance)
    for property_name, role in [('idle_clip', 'Idle'), ('walk_clip', 'Chase'), ('attack_clip', 'MeleeLeft'),
                               ('slow_walk_clip', 'SlowWalk'), ('chase_clip', 'Chase'),
                               ('melee_left_clip', 'MeleeLeft'), ('melee_right_clip', 'MeleeRight'),
                               ('death_clip', 'Death'), ('wall_listen_clip', 'WallListen')]:
        defaults.set_editor_property(property_name, clips[role])
    motion = json.loads((ROOT/'Motion/motion_manifest.json').read_text(encoding='utf-8'))
    left_contact = motion['clips']['MeleeLeft']['impact_seconds']
    right_contact = motion['clips']['MeleeRight']['impact_seconds']
    defaults.set_editor_property('left_contact_time', left_contact)
    defaults.set_editor_property('right_contact_time', right_contact)
    defaults.set_editor_property('contact_time', left_contact)
    defaults.set_editor_property('contact_end', left_contact + defaults.get_editor_property('contact_window_seconds'))
    defaults.set_editor_property('wall_mimic_sound', mimic)
    combat = defaults.get_editor_property('combat')
    combat.set_editor_property('hit_clip', clips['Hit'])
    combat.set_editor_property('dizzy_clip', clips['Dizzy'])
    knockdown = defaults.get_editor_property('knockdown')
    for property_name, role in [('fall_clip', 'Fall'), ('get_up_clip', 'GetUp'), ('prone_get_up_clip', 'ProneGetUp')]:
        knockdown.set_editor_property(property_name, clips[role])
    ai = u.load_class(None, '/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C')
    if not ai:
        raise RuntimeError('The shared monster Behavior Tree controller asset is unavailable.')
    defaults.set_editor_property('ai_controller_class', ai)
    LIB.set_metadata_tag(bp, 'Identity', 'M-07 盲祷者; 310 cm sensory containment experiment; whole body plus six living gill membranes')
    LIB.set_metadata_tag(bp, 'Tuning', 'Editable provisional local-playtest values; current shared health scaling and combat formulas apply')
    LIB.set_metadata_tag(bp, 'AI', 'Existing shared monster perception/Behavior Tree, melee authority, toughness and knockdown contracts')
    save(bp)
    record('character_blueprint', {'saved': True, 'asset': bp.get_path_name(), 'class': bp.generated_class().get_path_name(),
           'controller_class': ai.get_path_name(), 'left_contact_s': left_contact, 'right_contact_s': right_contact,
           'provisional_tuning': {'base_health': 420, 'damage': 36, 'level': 7, 'rank': 'Elite', 'walk_cm_s': 90,
                                  'chase_cm_s': 145, 'base_attack_range_cm': 180, 'capsule_radius_cm': 50,
                                  'capsule_half_height_cm': 155, 'nav_agent_height_cm': 312}})

if 'navigation' not in report['completed']:
    original = ROOT.parent.parent/'Content/GameMaps/DayNight_Lighting.umap'
    backup = ROOT/'Authoring'/'DayNight_Lighting.before-m07-navigation.umap'
    if not backup.exists():
        shutil.copy2(original, backup)
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
        receipt = json.loads(u.BlindSupplicantNavigationAuthoring.build_and_save_map_navigation(MAP))
    else:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        # Preserve any pre-existing map edits. The first compiled helper has
        # a late dirty-map guard; an already running editor can finish that
        # authoring operation through UE's own synchronous navigation command.
        dirty_maps = u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        if any(package.get_name() == MAP for package in dirty_maps):
            raise RuntimeError('The loaded DayNight map has pre-existing unsaved edits; no map was changed.')
        receipt = json.loads(u.BlindSupplicantNavigationAuthoring.build_and_save_navigation(world))
        if not receipt.get('saved') and receipt.get('error') == 'The loaded map contains existing unsaved edits; navigation authoring leaves it untouched.':
            u.SystemLibrary.execute_console_command(world, 'RebuildNavigation')
            saved = u.EditorLoadingAndSavingUtils.save_map(world, MAP)
            receipt = {
                'saved': bool(saved), 'navigation_built': True, 'runtime_tested': False,
                'map': MAP, 'profile_index': 4, 'radius_cm': 50, 'height_cm': 312,
                'authoring_operation': 'existing editor native profile setup; synchronous RebuildNavigation; save_map',
                'navigation_data': [actor.get_path_name() for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
                                    if actor.get_name() == 'RecastNavMesh-BlindSupplicantM07'],
            }
    if not receipt.get('saved') or not receipt.get('navigation_built'):
        raise RuntimeError('M07 navigation production did not save the map: ' + json.dumps(receipt, ensure_ascii=False))
    record('navigation', receipt)

report.update({'stage': 'M07 gameplay assets saved; awaiting user manual test',
               'gameplay_integrated': True, 'f6_registered': True,
               'f6': {'id': 'BlindSupplicantM07', 'label': '盲祷者 M-07', 'class': BP_PATH + '.BP_BlindSupplicantM07_C'},
               'runtime_tested': False, 'visual_tested': False})
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07 GAMEPLAY PRODUCTION SAVED; USER MANUAL TEST PENDING', flush=True)
