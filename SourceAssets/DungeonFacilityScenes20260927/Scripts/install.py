"""Publish into the current saved generator catalog, preserving unrelated edits and its existing room pool."""
import hashlib,json,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
receipt=json.loads((ROOT/'Receipts/import.json').read_text(encoding='utf-8'))
if receipt['stage']!='meshes_saved':raise RuntimeError('Complete mesh import before catalog installation')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active play; facility catalog install pending')
def dirty():return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
initial={p.get_name() for p in dirty()}
if any('/gamemaps/l_dungeon_randomized' in p.lower() for p in initial):raise RuntimeError('Preserve unsaved dungeon changes')
world=ue.get_editor_world() if ue else None
previous=world.get_path_name().split('.')[0] if world else None
if previous!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world:raise RuntimeError('Cannot load dungeon')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one dungeon generator')
g=generators[0];before=g.get_editor_property('module_catalog_json')
sources=ROOT/'Sources';sources.mkdir(exist_ok=True)
backup=sources/('catalog-before-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not backup.exists():backup.write_text(before,encoding='utf-8')
catalog=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['extend'](json.loads(before))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for value in receipt['meshes'].values():
    a=u.load_asset(value['path'])
    if not a:raise RuntimeError('Missing imported assembly '+value['path'])
    assets[a.get_path_name()]=a
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
packages=[p for p in dirty() if p.get_name() not in initial and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Generator catalog save failed')
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
result=dict(stage='map_saved',map=TARGET,saved_packages=[p.get_name() for p in packages],previous_map=previous,
    room_ids=catalog['room_ids'],room_scene_version=catalog['room_scene_version'],assemblies=len(receipt['meshes']),functional_recipes=9,
    states_per_recipe=3,maximum_added_parts_per_room=3,new_lights=0,loose_props_per_room_cap=8,tests_run=False)
(ROOT/'Receipts/install.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if ue and previous and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('FACILITY_CATALOG_SAVED',json.dumps(result,ensure_ascii=False),flush=True)
