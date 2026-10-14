from pathlib import Path
from collections import Counter
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
def describe(a):return dict(label=a.get_actor_label(),path=a.get_path_name(),type=a.get_class().get_name(),tags=[str(t) for t in a.tags])
def suspect(a):
    name=a.get_class().get_name().lower()
    return any(s in name for s in ('spawn','encounter','monst','zombie','wolf','maggot','handbrain','fleshhand','witch','mutant','progressiongate','roomgate'))
g=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
c=json.loads(g.get_editor_property('module_catalog_json'))
game=ed.get_game_world()
report=dict(editor=ed.get_editor_world().get_path_name(),game=game.get_path_name() if game else None,
    dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    actor_classes=dict(Counter(a.get_class().get_name() for a in actors)),suspects=[describe(a) for a in actors if suspect(a)],
    spawn_modules=[m['id'] for m in c['modules'] if m.get('spawn',{}).get('pool')],boss_modules=[m['id'] for m in c['modules'] if 'boss_encounter' in m],
    game_suspects=[describe(a) for a in u.GameplayStatics.get_all_actors_of_class(game,u.Actor) if suspect(a)] if game and 'L_Dungeon_Randomized' in game.get_path_name() else [])
(ROOT/'Receipts/world-before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('actor_classes','game_suspects')},ensure_ascii=False))
