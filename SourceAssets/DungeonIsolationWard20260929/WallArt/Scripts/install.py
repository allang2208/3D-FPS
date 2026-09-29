"""Persist poster recipes and hard references; no layout generation or scene preview."""
import hashlib,json,runpy
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];WARD=ROOT.parent;PROJECT=WARD.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('Preserve active PIE; wall art installation pending')
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
if len(generators)!=1:raise RuntimeError('Expected one production dungeon generator')
g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
index=next(i for i,m in enumerate(catalog['modules']) if m['id']=='AbandonedIsolationWard')
backup=ROOT/'Before';backup.mkdir(parents=True,exist_ok=True)
path=backup/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not path.exists():path.write_text(before,encoding='utf-8')
module=runpy.run_path(str(ROOT/'Scripts/author_layout.py'))['apply'](catalog['modules'][index])
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for entries in module['wall_art']['pools'].values():
    for entry in entries:
        for path in [entry['mesh']]+entry['materials']:
            if not path:continue
            a=u.load_asset(path)
            if not a:raise RuntimeError('Missing imported poster asset '+path)
            assets[a.get_path_name()]=a
catalog['modules'][index]=module
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
packages=[p for p in dirty() if p.get_name() not in initial and '/gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Wall art catalog save failed')
def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
write(WARD.parent/'DungeonRoutes20260922/Config/catalog.json',catalog)
write(WARD/'Config/module.json',module);write(ROOT/'layout.json',module['wall_art'])
report=dict(stage='map_saved',map=TARGET,module=module['id'],saved_packages=[p.get_name() for p in packages],
    pools={k:len(v) for k,v in module['wall_art']['pools'].items()},
    groups=[dict(id=g['id'],slots=len(g['slots']),count=[g['min_count'],g['max_count']]) for g in module['wall_art']['groups']],
    original_assets_modified=False,native_build_required=True,tests_run=False,rendered=False)
write(ROOT/'install.json',report)
if previous and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('WARD_WALL_ART_SAVED',json.dumps(report,ensure_ascii=False))
