import json
from pathlib import Path
import unreal

routes = [('/Game/Maps/DayNight_Lighting', '/Game/GameMaps/DayNight_Lighting'),
          ('/Game/SceneTests/Normandy/L_Normandy_FPS_Test', '/Game/GameMaps/L_Normandy_FPS_Test'),
          ('/Game/SceneTests/MilitaryTrench/L_MilitaryTrench_FPS_Test', '/Game/GameMaps/L_MilitaryTrench_FPS_Test')]
editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = []
for old, new in routes:
    assert not unreal.EditorAssetLibrary.does_asset_exist(new), 'Destination already exists: ' + new
    assert editor.load_level(old), 'Source load failed: ' + old
    before = len(actors.get_all_level_actors())
    world_asset = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rename = unreal.AssetRenameData(world_asset, '/Game/GameMaps', new.rsplit('/', 1)[1])
    assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets([rename]), 'Rename failed: ' + old
    assert editor.save_current_level(), 'Save failed: ' + new
    assert editor.load_level(new), 'Reload failed: ' + new
    after = len(actors.get_all_level_actors())
    assert before == after, 'Actor count changed: ' + new
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    report.append({'old': old, 'new': new, 'actors_before': before, 'actors_after': after,
                   'world': world.get_path_name()})
    unreal.log('MAP_ORGANIZED ' + json.dumps(report[-1]))
    (Path(unreal.Paths.project_saved_dir()) / 'SceneTests/map-organization.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('MAP_ORGANIZATION_OK')
