"""Read the authoritative hospital descriptors for the requested missing-container diagnosis."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
(ROOT/'Config').mkdir(exist_ok=True)
world=u.load_asset('/Game/GameMaps/L_Dungeon_Randomized')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
catalog=json.loads(generators[0].get_editor_property('module_catalog_json'))
(ROOT/'Config/latest-production.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);game=editor.get_game_world()
print(json.dumps(dict(game_world=game.get_path_name() if game else None,
    containers={m['id']:dict(groups=len(m.get('warehouse_containers',{}).get('groups',[])),revision=m.get('hospital_container_revision'),
    count_limits=[g['pick_count'] for g in m.get('warehouse_containers',{}).get('groups',[])])
    for m in catalog['modules'] if m['id'] in ('Drainage','AbandonedIsolationWard','AbandonedAnatomyTheatre')}),ensure_ascii=False),flush=True)
