import json
from pathlib import Path
import unreal as u

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_editor_world()
game = editor.get_game_world()
report = {'editor_world': world.get_path_name() if world else None,
          'game_world': game.get_path_name() if game else None,
          'dirty_maps': [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
          'actors': []}
if game and 'L_TemperateHills_Initial' in game.get_path_name():
    report['hills_runtime'] = []
    classes = [u.DirectionalLight, u.SkyLight, u.SkyAtmosphere, u.FPSWeatherManager,
               u.load_object(None, '/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C')]
    for cls in classes:
        for actor in u.GameplayStatics.get_all_actors_of_class(game, cls):
            row = {'name': actor.get_name(), 'class': actor.get_class().get_name(), 'lights': []}
            if isinstance(actor, u.FPSWeatherManager):
                row['clock'] = actor.get_editor_property('normalized_day_time')
            for component in actor.get_components_by_class(u.SceneComponent):
                if isinstance(component, (u.LightComponent, u.SkyLightComponent)):
                    row['lights'].append({'name': component.get_name(),
                                          'intensity': component.get_editor_property('intensity'),
                                          'visible': component.get_editor_property('visible')})
            report['hills_runtime'].append(row)
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor, (u.DirectionalLight, u.SkyLight, u.SkyAtmosphere)) or 'Ultra_Dynamic_Sky' in actor.get_class().get_name():
        report['actors'].append({'name': actor.get_name(), 'class': actor.get_class().get_path_name()})
Path('D:/FPS3D/FPSGAME/SourceAssets/HillsNightRepair20261114/editor-state.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
