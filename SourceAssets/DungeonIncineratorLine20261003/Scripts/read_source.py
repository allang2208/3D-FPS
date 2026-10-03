"""Read saved treatment-route descriptors for preview authoring; never run a game."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
PRODUCTION = '/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Preserve active game session')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:
    raise RuntimeError('Preserve unsaved maps: ' + str(dirty))
original = editor.get_editor_world().get_path_name().split('.')[0]
try:
    world = u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
    generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
    if len(generators) != 1:
        raise RuntimeError('Saved production generator unavailable')
    text = generators[0].get_editor_property('module_catalog_json')
    catalog = json.loads(text)
    route = next(r for r in catalog['themed_routes']['routes'] if r['id'] == 'treatment')
    selected = [m for m in catalog['modules'] if m['id'] in route['sequence'] + ['Transit']]
    (ROOT / 'Config').mkdir(parents=True, exist_ok=True)
    (ROOT / 'Config/source-modules.json').write_text(json.dumps(dict(
        source_map=PRODUCTION, source_catalog_sha256=hashlib.sha256(text.encode()).hexdigest(),
        route=route, modules=selected), ensure_ascii=False, indent=2), encoding='utf8')
    print('INCINERATOR_SOURCE ' + json.dumps([dict(id=m['id'], parts=len(m['parts']),
        lights=len(m['lights']), ports=m['ports'], runtime_types=[s['type'] for s in m.get('runtime_actors', [])],
        scene_recipes=[r['id'] for r in m.get('scene_recipes', [])], props=m.get('props'),
        progression_gate=m.get('progression_gate'), containers=m.get('warehouse_containers')) for m in selected]))
finally:
    if original != PRODUCTION:
        u.EditorLoadingAndSavingUtils.load_map(original)
