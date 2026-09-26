"""Install repaired catalog, sealed entry and persistent runtime navigation template."""
import json,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];TARGET='/Game/GameMaps/L_Dungeon_Randomized'
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);ed=u.get_editor_subsystem(u.LevelEditorSubsystem);aa=u.get_editor_subsystem(u.EditorActorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve active play; installation pending')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if any('/gamemaps/l_dungeon_randomized' in p.get_name().lower() for p in dirty):raise RuntimeError('Preserve unsaved randomized-map edits')
if ue.get_editor_world().get_path_name().split('.')[0]!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    if not ed.load_level(TARGET):raise RuntimeError('Unable to open dungeon map')
actors=list(aa.get_all_level_actors());g=next(a for a in actors if a.get_actor_label()=='DGN_RouteGenerator')
previous=g.get_editor_property('module_catalog_json');catalog=json.loads(previous)
previous_assets=list(g.get_editor_property('module_assets'))
(ROOT/'Sources/catalog-before.json').write_text(previous,encoding='utf-8')
extra=ROOT.parent/'DungeonVentFreight20260922'
data=json.loads((extra/'Config/modules.json').read_text(encoding='utf-8'))
# Every candidate dependency must already exist before the active pool is changed.
for m in data['modules']:
    for p in m['parts']:
        if not u.EditorAssetLibrary.does_asset_exist(p['mesh']):raise RuntimeError('New room import incomplete: '+p['mesh'])
ids=set(data['room_ids']);catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+data['modules']
catalog['room_ids']=list(dict.fromkeys(catalog.get('room_ids',['Distribution','Drainage','ShoredBreach'])+data['room_ids']))
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](catalog)
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
paths=[]
for module in catalog['modules']:
    for p in module['parts']+[p for side in module.get('side_sockets',[]) for p in side['parts']]:paths.extend([p['mesh']]+p['materials'])
    for p in module.get('props',[]):paths.extend([p['skeletal_mesh'],p['closed_animation']]+list(p['material_overrides'].values()))
    if module.get('boss_encounter'):
        encounter=module['boss_encounter'];paths.extend([encounter['class'],encounter['gate_material']])
    # Spawn pools ride the same catalog-driven collection; present only once DungeonSpawn20260925 is installed.
    for entry in module.get('spawn',{}).get('pool',[]):paths.append(entry['class'])
paths.append(catalog['start_connection']['mesh'])
for path in dict.fromkeys(paths):
    if not path:continue
    # load_class is the reliable route for BP *_C and native /Script/ classes (spawn pools) alike.
    asset=u.load_class(None,path) if (path.endswith('_C') or path.startswith('/Script/')) else u.load_asset(path)
    if not asset:raise RuntimeError('Missing repaired dependency '+path)
    assets[asset.get_path_name()]=asset
navigation=next((a for a in actors if a.actor_has_tag('DungeonRouteNavigation')),None)
if not navigation:
    # This authors a persistent brush; native runtime only moves/scales it, no editor API required in game.
    if not u.MonsterAIController.build_navigation_bounds(ue.get_editor_world(),u.Vector(0,0,-10000),u.Vector(50,50,50)):
        raise RuntimeError('Unable to author navigation template')
    navigation=next(a for a in aa.get_all_level_actors() if a.actor_has_tag('MonsterNavigation'))
    navigation.modify();navigation.set_actor_label('DGN_RuntimeNavigation');navigation.set_folder_path('DungeonRoutes/Navigation')
    navigation.set_editor_property('tags',list(navigation.tags)+[u.Name('DungeonRouteNavigation')])
    navigation.get_component_by_class(u.BrushComponent).set_mobility(u.ComponentMobility.MOVABLE)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
g.call_method('GeneratePreview')
if not g.actor_has_tag('DungeonAssembly.Ready') or g.actor_has_tag('DungeonAssembly.Failed'):
    g.set_editor_property('module_catalog_json',previous)
    g.set_editor_property('module_assets',previous_assets)
    raise RuntimeError('Assembly incomplete: original catalog restored, no map saved')
start=next(a for a in actors if a.get_actor_label()=='DGN_Link_A_B')
start.modify();start.get_component_by_class(u.StaticMeshComponent).set_static_mesh(u.load_asset(catalog['start_connection']['mesh']))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save dungeon actor packages')
if not ed.save_current_level():raise RuntimeError('Cannot save dungeon level')
routes=ROOT.parent/'DungeonRoutes20260922'
(routes/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
registry=routes/'Config/room-extensions.json';entries=json.loads(registry.read_text()) if registry.exists() else []
entry='DungeonVentFreight20260922/Config/modules.json'
if entry not in entries:entries.append(entry)
registry.write_text(json.dumps(entries,indent=2),encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,description=g.get_editor_property('layout_description'),room_ids=catalog['room_ids'],boss_terminal_enabled=catalog['boss_terminal_enabled'],tests_run=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('DUNGEON_REPAIRS_INSTALLED',g.get_editor_property('layout_description'))
