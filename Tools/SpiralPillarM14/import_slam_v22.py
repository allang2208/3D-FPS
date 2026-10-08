"""Import and save the sharp M14 trunk slam, impact wave and contact clock."""
from pathlib import Path
import json
import shutil
import traceback
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/SpiralPillarM14Meshy20261004/ProductionV22'
PLAN = json.loads(Path(__file__).with_name('slam_v22.json').read_text(encoding='utf8'))
DEST = '/Game/Monsters/SpiralPillarM14'
BP_PATH = DEST + '/BP_SpiralPillarM14'
CLIP_PATH = DEST + '/Animations/' + PLAN['action']
SOUND_PATH = DEST + '/Audio/SlamV22/' + PLAN['sound']
LIB = u.EditorAssetLibrary
REPORT_PATH = ROOT / 'Records/ue_revision.json'
report = dict(revision=PLAN['revision'], complete=False, saved=[], native_code_changed=True,
              runtime_tested=False, preview_rendered=False, audio_listened=False)

def record():
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()

def owned(path):
    if not LIB.does_asset_exist(path):
        return None
    asset = u.load_asset(path)
    if LIB.get_metadata_tag(asset, 'M14.SlamRevision') != PLAN['revision']:
        raise RuntimeError('Preserving existing asset at ' + path)
    return asset

def backup(package):
    relative = package.removeprefix('/Game/') + '.uasset'
    source, target = PROJECT / 'Content' / relative, ROOT / 'Before' / relative
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

def main():
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if editor and editor.get_game_world():
            raise RuntimeError('PIE is active; asset import has not started')
    bp = u.load_asset(BP_PATH)
    cdo = u.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property('visual_mesh')
    skeleton = mesh.skeleton
    targets = {BP_PATH, CLIP_PATH, SOUND_PATH, skeleton.get_path_name().split('.')[0]}
    dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
             if p.get_name() in targets]
    if dirty:
        raise RuntimeError('Preserving unsaved target packages: ' + ', '.join(dirty))
    backup(BP_PATH)
    backup(skeleton.get_path_name().split('.')[0])
    previous = {}
    for name in ('bite_clip', 'bite_sound', 'visual_mesh', 'death_clip', 'idle_clip', 'move_clip',
                 'turn_left_clip', 'turn_right_clip', 'spit_clip', 'sweep_positive_clip',
                 'sweep_negative_clip', 'trunk_slam_clip', 'trunk_slam_sound'):
        asset = cdo.get_editor_property(name)
        previous[name] = asset.get_path_name() if asset else None
    for name in ('bite_contact_seconds', 'bite_cooldown', 'bite_trigger_range', 'mouth_reach', 'physical_attack', 'slam_contact_seconds', 'slam_cooldown', 'slam_min_range', 'slam_trigger_range', 'slam_damage_multiplier', 'slam_body_radius'):
        previous[name] = float(cdo.get_editor_property(name))
    report['before'] = previous
    record()
    source_clip = DEST + '/Animations/' + PLAN['source_action']
    if previous['trunk_slam_clip'].split('.')[0] not in (source_clip, CLIP_PATH):
        raise RuntimeError('The active slam changed after authoring; preserving the newer binding')

    clip = owned(CLIP_PATH)
    if clip is None:
        old = u.SystemLibrary.get_console_variable_bool_value('Interchange.FeatureFlags.Import.FBX')
        try:
            u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
            task = u.AssetImportTask()
            task.filename = str(ROOT / 'Exports' / (PLAN['action'] + '.fbx'))
            task.destination_path = DEST + '/Animations'
            task.destination_name = PLAN['action']
            task.automated, task.save, task.replace_existing = True, False, False
            task.factory = u.FbxFactory()
            options = u.FbxImportUI()
            options.automated_import_should_detect_type = False
            options.import_as_skeletal = True
            options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
            options.import_mesh, options.import_animations = False, True
            options.import_materials, options.import_textures = False, False
            options.skeleton = skeleton
            data = options.anim_sequence_import_data
            data.convert_scene, data.convert_scene_unit, data.import_uniform_scale = True, True, 1.
            data.set_editor_property('use_default_sample_rate', False)
            data.set_editor_property('custom_sample_rate', PLAN['export_fps'])
            data.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
            task.options = options
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        finally:
            u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX ' + ('1' if old else '0'))
        clip = u.load_asset(CLIP_PATH)
        if not clip:
            raise RuntimeError('Animation import did not produce ' + CLIP_PATH)
        LIB.set_metadata_tag(clip, 'M14.SlamRevision', PLAN['revision'])
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('loop', False)
    clip.set_preview_skeletal_mesh(mesh)
    save(clip)
    save(skeleton)

    sound = owned(SOUND_PATH)
    if sound is None:
        task = u.AssetImportTask()
        task.filename = str(ROOT / 'Audio' / (PLAN['sound'] + '.wav'))
        task.destination_path, task.destination_name = SOUND_PATH.rsplit('/', 1)
        task.automated, task.save, task.replace_existing = True, False, False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sound = u.load_asset(SOUND_PATH)
        if not sound:
            raise RuntimeError('Audio import did not produce ' + SOUND_PATH)
        LIB.set_metadata_tag(sound, 'M14.SlamRevision', PLAN['revision'])
    sound.set_editor_property('looping', False)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    save(sound)

    # Bind all three parts together only after both new assets have saved.
    cdo.set_editor_property('trunk_slam_clip', clip)
    cdo.set_editor_property('trunk_slam_sound', sound)
    cdo.set_editor_property('slam_contact_seconds', PLAN['contact_seconds'])
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    report.update(complete=True, blueprint=bp.get_path_name(), slam_animation=clip.get_path_name(),
                  slam_sound=sound.get_path_name(), contact_seconds=PLAN['contact_seconds'],
                  duration_seconds=PLAN['duration_seconds'],
                  changed_defaults=['trunk_slam_clip', 'trunk_slam_sound', 'slam_contact_seconds'],
                  stun_seconds=PLAN['stun_seconds'], knockback_cm=PLAN['knockback_cm'],
                  damage_range_cooldown_and_other_actions_preserved=True, user_testing_pending=True)
    record()
    print('M14_V22_SLAM_SAVED ' + json.dumps(report, ensure_ascii=False))

try:
    main()
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
