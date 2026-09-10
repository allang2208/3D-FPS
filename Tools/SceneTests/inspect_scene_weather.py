import json
from pathlib import Path
import unreal

editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {}
for name in ['DayNight_Lighting', 'L_Normandy_FPS_Test', 'L_MilitaryTrench_FPS_Test']:
    assert editor.load_level('/Game/GameMaps/' + name)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rows = []
    for a in actors_api.get_all_level_actors():
        cls = a.get_class().get_name()
        if any(x.lower() in (cls + a.get_actor_label()).lower() for x in ['sky', 'sun', 'cloud', 'fog', 'light', 'weather', 'sequence']):
            row = dict(label=a.get_actor_label(), cls=cls, path=a.get_path_name())
            if 'DayNight' in cls:
                row['properties'] = {}
                for prop in dir(a):
                    if any(x in prop for x in ['sun', 'time', 'speed', 'cycle', 'cloud']):
                        try: row['properties'][prop] = str(a.get_editor_property(prop))
                        except Exception: pass
            rows.append(row)
    report[name] = dict(game_mode=str(world.get_world_settings().get_editor_property('default_game_mode')), actors=rows)
out = Path(unreal.Paths.project_saved_dir()) / 'WeatherPanel'
out.mkdir(exist_ok=True)
(out / 'scene-weather-before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('SCENE_WEATHER_INSPECTION_OK')
