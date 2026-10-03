"""Read saved treatment geometry for authoring; preserve the current editor map."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if editor.get_game_world():raise RuntimeError('Preserve active game session')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps: '+str(dirty))
original=editor.get_editor_world().get_path_name().split('.')[0]
try:
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
    generator=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
    catalog=json.loads(generator.get_editor_property('module_catalog_json'))
    ids=['Transit','ShoredBreach','AbandonedIncineratorHall','AbandonedFlueGasStation']
    data=dict(modules=[m for m in catalog['modules'] if m['id'] in ids],source_map='/Game/GameMaps/L_Dungeon_Randomized')
    (ROOT/'Config/placement-source.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print('TREATMENT_PLACEMENT_SOURCE_SAVED '+str(len(data['modules'])))
finally:
    if original and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        u.EditorLoadingAndSavingUtils.load_map(original)
