import json
from pathlib import Path
import unreal

source = '/Game/MilitaryTrench/Tutorial/Scenes/Scene_Trench_Tutorial'
target = '/Game/GameMaps/L_MilitaryTrench_FPS_Test'
editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not unreal.EditorAssetLibrary.does_asset_exist(target), 'Refusing to overwrite existing test map'
assert editor.new_level_from_template(target, source), 'Template creation failed'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = actors_api.get_all_level_actors()
assert len(actors) >= 457, 'Source actors were not preserved'
starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
assert len(starts) == 1, 'Expected original pack PlayerStart'
for actor in actors:
    if isinstance(actor, unreal.LevelSequenceActor):
        settings = actor.get_editor_property('playback_settings')
        settings.set_editor_property('auto_play', False)
        actor.set_editor_property('playback_settings', settings)
world.get_world_settings().set_editor_property('default_game_mode', unreal.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode'))
camera = next(a for a in actors if a.get_actor_label() == 'Cam_01_Main')
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(), camera.get_actor_rotation())
assert editor.save_current_level(), 'Save failed'
assert editor.load_level(target), 'Reload failed'
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
loaded = actors_api.get_all_level_actors()
assert len(loaded) >= 457, 'Reload lost actors'
assert world.get_world_settings().get_editor_property('default_game_mode') == unreal.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode')
start = next(a for a in loaded if isinstance(a, unreal.PlayerStart))
p = start.get_actor_location()
report = {'map': target, 'source': source, 'actor_count': len(loaded),
          'player_start': [p.x, p.y, p.z], 'component_overview': '/Game/MilitaryTrench/Maps/AssetZoo',
          'validation': 'Source PlayerStart retained; saved and reloaded with FPS mode; runtime pending'}
out = Path(unreal.Paths.project_saved_dir()) / 'SceneTests'
(out / 'trench-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('TRENCH_BUILD_OK ' + json.dumps(report))
