"""Bind the frozen spawn pools to the live generator; do not run generation or PIE."""
import json,runpy
from pathlib import Path
try:
    import unreal
except ImportError:
    pass
if 'unreal' not in globals():
    raise SystemExit('DungeonSpawn20260925 install.py requires UE editor Python: run it headless via UnrealEditor-Cmd -run=pythonscript, not with system python')
u=unreal
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play; spawn installation pending')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if any('/gamemaps/l_dungeon_randomized' in p.get_name().lower() for p in dirty):raise RuntimeError('Preserve unsaved dungeon changes')
world=ue.get_editor_world() if ue else None
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world:raise RuntimeError('Cannot load dungeon for spawn binding')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one dungeon generator')
g=generators[0];previous=g.get_editor_property('module_catalog_json')
backup=ROOT/'Sources/catalog-before.json'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():backup.write_text(previous,encoding='utf-8')
scripts=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=scripts['extend'](json.loads(previous))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
paths=list(scripts['asset_paths'](catalog))
for path in dict.fromkeys(paths):
    if not path:continue
    # load_class is the reliable route for BP *_C and native /Script/ classes alike.
    asset=u.load_class(None,path) if (path.endswith('_C') or path.startswith('/Script/')) else u.load_asset(path)
    if not asset:raise RuntimeError('Missing spawn dependency '+path)
    assets[asset.get_path_name()]=asset
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
# This OFPA map stores the generator in an external actor package. Save the
# target's newly dirty packages, without including unrelated content packages.
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save generator package')
# The existing actor GUID/level topology is unchanged; resaving the root .umap
# is unnecessary and may conflict with another process holding it open.
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts').mkdir(parents=True,exist_ok=True)
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,room_ids=catalog['room_ids'],
    spawn_modules=sum(1 for m in catalog['modules'] if m.get('spawn',{}).get('source')=='DungeonSpawn20260925'),
    spawn_assets=len(paths),saved_actor_packages=[p.get_name() for p in owned],root_map_modified=False,tests_run=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('DUNGEON_SPAWN_CATALOG_SAVED',catalog['room_ids'],flush=True)
