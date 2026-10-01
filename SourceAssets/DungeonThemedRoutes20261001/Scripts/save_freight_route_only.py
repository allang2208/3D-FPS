"""Save only the freight selection change in the production map; no generation."""
import hashlib,json,runpy,shutil
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Background commandlet required')
target='/Game/GameMaps/L_Dungeon_Randomized'
source=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
backup_dir=ROOT/'Backup/FreightRouteOnly'
backup_dir.mkdir(parents=True,exist_ok=True)
digest=hashlib.sha256(source.read_bytes()).hexdigest()
backup=backup_dir/f'L_Dungeon_Randomized-{digest[:12]}.umap'
if not backup.exists():
    shutil.copy2(source,backup)
world=u.EditorLoadingAndSavingUtils.load_map(target)
if not world:
    raise RuntimeError('Production map unavailable')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:
    raise RuntimeError('Production generator unavailable')
generator=generators[0]
before=generator.get_editor_property('module_catalog_json')
(backup_dir/f'catalog-{digest[:12]}.json').write_text(before,encoding='utf-8')
apply=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))['restrict_freight_to_theme']
catalog=apply(json.loads(before))
generator.modify()
generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):
    raise RuntimeError('Production map not saved')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for dest in (ROOT/'Config/catalog.json',PROJECT/'SourceAssets/DungeonSplitLevels20261001/Config/catalog.json',
             PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json'):
    dest.write_text(text,encoding='utf-8')
report=dict(stage='map_saved',map=target,prior_map_sha256=digest,backup=str(backup),
    removed_room_ids=sorted(set(json.loads(before)['room_ids'])-set(catalog['room_ids'])),
    transition_families=catalog['themed_routes']['transition_families'],
    assets_reimported=False,tests_run=False,generation_executed=False,editor_opened=False)
(ROOT/'Receipts/freight-route-only-20261001.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('FREIGHT_ROUTE_ONLY_MAP_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
