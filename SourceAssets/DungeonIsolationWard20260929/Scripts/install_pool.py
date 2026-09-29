"""Import and save the production ward room. Does not generate, play or test a layout."""
import hashlib,json,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active PIE; ward pool save pending')
def dirty():return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
initial={p.get_name() for p in dirty()}
if any('/gamemaps/l_dungeon_randomized' in p.lower() for p in initial):raise RuntimeError('Preserve unsaved dungeon')
world=ue.get_editor_world() if ue else None
previous=world.get_path_name().split('.')[0] if world else None
if previous!=TARGET and u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
man=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf-8'))
# Existing doors, shards and furniture are retained as their already saved assets.
runpy.run_path(str(ROOT/'Scripts/import_assets.py'),run_name='__main__',
    init_globals={'WARD_IMPORT_NAMES':{i['name'] for i in man['objects'] if i['kind']!='ObservationGlass' and not i['sample_only']}})
module=runpy.run_path(str(ROOT/'Scripts/build_pool_module.py'))['build']()
if previous!=TARGET:
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    if not world:raise RuntimeError('Cannot load production dungeon')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Expected one production dungeon generator')
g=generators[0];before=g.get_editor_property('module_catalog_json')
backup=ROOT/'SourceBackup/BeforePoolV9';backup.mkdir(parents=True,exist_ok=True)
path=backup/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not path.exists():path.write_text(before,encoding='utf-8')
scripts=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=scripts['extend'](json.loads(before),module)
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for path in dict.fromkeys(scripts['asset_paths'](module)):
    item=u.load_class(None,path) if path.startswith('/Script/') or path.endswith('_C') else u.load_asset(path)
    if not item:raise RuntimeError('Missing ward runtime asset '+path)
    assets[item.get_path_name()]=item
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
packages=[p for p in dirty() if p.get_name() not in initial and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Ward pool save failed')
(ROOT.parent/'DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/module.json').write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf-8')
draft_path=ROOT/'Config/module-draft.json'
draft=json.loads(draft_path.read_text(encoding='utf-8'))
draft.update(status='registered_in_random_pool',revision=module['revision'],ports=module['ports'],
    pool_coordinate_system='UE centimetres',production_module='Config/module.json',sample_portal_included=False)
draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
result=dict(stage='map_saved',map=TARGET,module=module['id'],revision=module['revision'],room_ids=catalog['room_ids'],
    saved_actor_packages=[p.get_name() for p in packages],selection=module['selection'],
    parts=len(module['parts']),runtime_actors=len(module['runtime_actors']),lights=len(module['lights']),
    spawn_count=module['spawn']['count'],spawn_pool=module['spawn']['pool'],sealed_encounter=True,
    ports=module['ports'],decon_external_entry='sealed',decon_internal_door='retained',portal_included=False,
    floor_blood_scale=2.5,floor_blood_width_cm=[87.5,212.5],wall_blood_width_cm=[35,85],
    tests_run=False,rendered=False)
(ROOT/'Receipts/pool-install.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
if previous and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('WARD_POOL_SAVED',json.dumps(result,ensure_ascii=False),flush=True)
