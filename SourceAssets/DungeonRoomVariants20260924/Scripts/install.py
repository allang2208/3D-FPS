"""Publish the catalog and saved dependencies; do not run generation or PIE."""
import json,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play; catalog installation pending')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if any('/gamemaps/l_dungeon_randomized' in p.get_name().lower() for p in dirty):raise RuntimeError('Preserve unsaved dungeon changes')
world=ue.get_editor_world() if ue else None
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world:raise RuntimeError('Cannot load dungeon for catalog binding')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one dungeon generator')
g=generators[0];previous=g.get_editor_property('module_catalog_json')
backup=ROOT/'Sources/catalog-before.json'
if not backup.exists():backup.write_text(previous,encoding='utf-8')
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](json.loads(previous))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
paths=set(json.loads((ROOT/'Receipts/import.json').read_text())['meshes'].values())
for path in sorted(paths):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing saved dependency '+path)
    assets[a.get_path_name()]=a
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
# This OFPA map stores the generator in an external actor package. Save the
# target's newly dirty packages, without including unrelated content packages.
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Cannot save generator package')
# The existing actor GUID/level topology is unchanged. Its OFPA package above
# owns both properties; resaving the root .umap is unnecessary and may conflict
# with another process holding a read handle to that unchanged map.
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/modules.json').write_text(json.dumps(dict(modules=[m for m in catalog['modules'] if m['id']!=m.get('family_id',m['id'])]),ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,room_ids=catalog['room_ids'],new_meshes=len(paths),
    saved_actor_packages=[p.get_name() for p in owned],root_map_modified=False,tests_run=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('ROOM_VARIANTS_CATALOG_SAVED',catalog['room_ids'],flush=True)
