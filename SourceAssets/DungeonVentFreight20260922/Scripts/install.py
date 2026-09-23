"""Append two complete authored rooms to the live catalog and save their references."""
import json,gc,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
if UE.get_game_world():raise RuntimeError('Preserve active play; room integration pending')
current=UE.get_editor_world().get_path_name().split('.')[0]
dirty_before=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if current!=TARGET and u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved open map')
if any('/gamemaps/l_dungeon_randomized' in p.get_name().lower() for p in dirty_before):raise RuntimeError('Preserve existing unsaved randomized dungeon edits')
if current!=TARGET and not ED.load_level(TARGET):raise RuntimeError('Cannot open target map')
g=next((a for a in AA.get_all_level_actors() if a.get_actor_label()=='DGN_RouteGenerator'),None)
if not g:raise RuntimeError('Target authored generator is missing')
old_json=g.get_editor_property('module_catalog_json')
old_assets=list(g.get_editor_property('module_assets'))
catalog=json.loads(old_json)
extension=json.loads((ROOT/'Config/modules.json').read_text(encoding='utf-8'))
ids=set(extension['room_ids'])
(ROOT/'Sources/catalog-before.json').write_text(old_json,encoding='utf-8')
catalog['modules']=[m for m in catalog['modules'] if m['id'] not in ids]+extension['modules']
catalog['room_ids']=list(dict.fromkeys(catalog.get('room_ids',['Distribution','Drainage','ShoredBreach'])+extension['room_ids']))
repair=ROOT.parent/'DungeonRouteRepairs20260922'
if (repair/'Receipts/import.json').exists():catalog=runpy.run_path(str(repair/'Scripts/extend_catalog.py'))['extend'](catalog)
assets={a.get_path_name():a for a in old_assets if a}
for module in catalog['modules']:
    if module.get('boss_encounter'):
        encounter=module['boss_encounter']
        for path in (encounter['class'],encounter['gate_material']):
            asset=u.load_class(None,path) if path.endswith('_C') else u.load_asset(path)
            if not asset:raise RuntimeError('Missing boss dependency '+path)
            assets[asset.get_path_name()]=asset
    for part in module['parts']+[p for side in module.get('side_sockets',[]) for p in side['parts']]:
        mesh=u.load_asset(part['mesh'])
        if not mesh:raise RuntimeError('Missing authored room asset '+part['mesh'])
        assets[mesh.get_path_name()]=mesh
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
# This is the authored map assembly operation, not PIE or a validation run.
old_description=g.get_editor_property('layout_description')
g.set_editor_property('layout_description','')
g.call_method('GeneratePreview')
if not g.actor_has_tag('DungeonAssembly.Ready') or g.actor_has_tag('DungeonAssembly.Failed'):
    g.set_editor_property('module_catalog_json',old_json)
    g.set_editor_property('module_assets',old_assets)
    g.set_editor_property('layout_description',old_description)
    raise RuntimeError('Room assembly did not complete; original catalog retained')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save authored map actor packages')
if not ED.save_current_level():raise RuntimeError('Cannot save authored map')
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,room_ids=catalog['room_ids'],new_modules=extension['room_ids'],mesh_count=sum(len(m['parts']) for m in extension['modules']),saved_packages=len(owned),description=g.get_editor_property('layout_description'),tests_run=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('VENT_FREIGHT_MAP_SAVED',json.dumps(extension['room_ids']),len(owned))
