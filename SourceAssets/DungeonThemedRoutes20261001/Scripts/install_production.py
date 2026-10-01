"""Save the accepted thematic catalog and hard dependencies; never generate/play."""
import hashlib,json,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use background commandlet')
receipt=json.loads((ROOT/'Receipts/import.json').read_text('utf-8'))
if receipt.get('stage')!='assets_saved_warehouse_captured':raise RuntimeError('Import and capture first')
source_map=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap'
digest=hashlib.sha256(source_map.read_bytes()).hexdigest()
backup_map=ROOT/'Backup'/('L_Dungeon_Randomized-'+digest[:12]+'.umap')
if not backup_map.exists():shutil.copy2(source_map,backup_map)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json')
backup=ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not backup.exists():backup.write_text(before,encoding='utf-8')
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
previous=json.loads(before);catalog=helpers['extend'](previous)
previous_paths=set(helpers['asset_paths'](previous))
paths=set(helpers['asset_paths'](catalog))-previous_paths
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for path in sorted(paths):
    # Provenance records also contain package directories, which are not assets.
    if path.startswith('/Game/') and u.EditorAssetLibrary.does_directory_exist(path):continue
    a=u.load_class(None,path) if path.startswith('/Script/') or ('.' in path and path.endswith('_C')) else u.load_asset(path)
    if not a:raise RuntimeError('Missing production dependency '+path)
    assets[a.get_path_name()]=a
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map not saved')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
(ROOT/'Config/catalog.json').write_text(text,encoding='utf-8')
(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(text,encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',map=TARGET,
    generator_version=8,routes=catalog['themed_routes'],hard_dependencies=len(assets),
    saved_packages=[TARGET],prior_map_sha256=digest,
    tests_run=False,editor_opened=False,generation_executed=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('THEMED_ROUTES_PRODUCTION_SAVED',flush=True)
