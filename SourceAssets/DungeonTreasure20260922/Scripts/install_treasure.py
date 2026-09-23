"""Register the treasure pool and generate the existing preview seed after native compilation."""
import unreal as u,json,runpy,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];ROUTES=ROOT.parent/'DungeonRoutes20260922';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);ed=u.get_editor_subsystem(u.LevelEditorSubsystem);aa=u.get_editor_subsystem(u.EditorActorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve running game')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
if ue.get_editor_world().get_path_name().split('.')[0]!=TARGET and not ed.load_level(TARGET):raise RuntimeError('Cannot open random dungeon')
g=next(a for a in aa.get_all_level_actors() if a.get_actor_label()=='DGN_RouteGenerator')
extension=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=extension['extend'](json.loads(g.get_editor_property('module_catalog_json')))
repair=ROOT.parent/'DungeonRouteRepairs20260922'
if (repair/'Receipts/import.json').exists():catalog=runpy.run_path(str(repair/'Scripts/extend_catalog.py'))['extend'](catalog)
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
paths=list(extension['asset_paths'](catalog))
for module in catalog['modules']:
    for p in module['parts']:paths.extend([p['mesh']]+p['materials'])
for path in paths:
    if path not in assets:
        asset=u.load_class(None,path) if path.endswith('_C') else u.load_asset(path)
        if not asset:raise RuntimeError('Missing treasure asset '+path)
        assets[path]=asset
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog));g.set_editor_property('module_assets',list(assets.values()))
g.call_method('GeneratePreview')
if not g.actor_has_tag('DungeonAssembly.Ready') or g.actor_has_tag('DungeonAssembly.Failed'):
    raise RuntimeError('Treasure assembly did not complete; do not save partial map')
graph=json.loads(g.get_editor_property('layout_manifest_json'))
if 'treasure_rooms' not in graph:raise RuntimeError('Treasure native code is not loaded; do not save the new catalogue before compilation')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Treasure external actor save failed')
if not ed.save_current_level():raise RuntimeError('Treasure map save failed')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,description=g.get_editor_property('layout_description'),treasure_rooms=graph['treasure_rooms'],probability_per_ordinary_room=.1,saved_packages=len(owned),tests_run=False),indent=2))
(ROOT/'Receipts/installed-layout.json').write_text(json.dumps(graph,indent=2))
(ROUTES/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
print('TREASURE_RANDOM_MAP_SAVED',g.get_editor_property('layout_description'))
