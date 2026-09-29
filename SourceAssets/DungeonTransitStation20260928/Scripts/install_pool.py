"""Save station module/dependencies in the existing generator, without generating a layout."""
import hashlib,json,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active PIE; station pool installation pending')
def dirty():return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
initial={p.get_name() for p in dirty()}
if any('/gamemaps/l_dungeon_randomized' in p.lower() for p in initial):raise RuntimeError('Preserve unsaved dungeon')
world=ue.get_editor_world() if ue else None
previous=world.get_path_name().split('.')[0] if world else None
if previous!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world:raise RuntimeError('Cannot load production dungeon')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one dungeon generator')
g=generators[0];before=g.get_editor_property('module_catalog_json')
backup=ROOT/'SourceBackup'/'BeforePoolIntegration20260929';backup.mkdir(parents=True,exist_ok=True)
path=backup/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not path.exists():path.write_text(before,encoding='utf-8')
scripts=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=scripts['extend'](json.loads(before));module=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for asset_path in dict.fromkeys(scripts['asset_paths'](module)):
    asset=u.load_class(None,asset_path) if asset_path.endswith('_C') or asset_path.startswith('/Script/') else u.load_asset(asset_path)
    if not asset:raise RuntimeError('Missing station dependency '+asset_path)
    assets[asset.get_path_name()]=asset
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
packages=[p for p in dirty() if p.get_name() not in initial and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Station pool save failed')
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/module.json').write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf-8')
result=dict(stage='map_saved',map=TARGET,module=module['id'],room_ids=catalog['room_ids'],
    saved_actor_packages=[p.get_name() for p in packages],selection=module['selection'],
    parts=len(module['parts']),lights=len(module['lights']),spawn_count=module['spawn']['count'],
    spawn_anchors=len(module['anchors']),sealed_encounter=True,portal_included=False,sample_caps_included=False,
    standalone_retirement='pending',tests_run=False,rendered=False)
(ROOT/'Receipts/pool-install.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if previous and previous!=TARGET and previous!='/Game/GameMaps/Design/L_AbandonedTransitStation_Subject':
    u.EditorLoadingAndSavingUtils.load_map(previous)
print('STATION_POOL_SAVED',json.dumps(result,ensure_ascii=False),flush=True)
