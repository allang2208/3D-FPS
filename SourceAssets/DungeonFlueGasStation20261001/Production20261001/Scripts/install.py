"""Save accepted module and hard dependencies in the existing production map."""
import json,hashlib,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[2]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Use background commandlet')
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
gs=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(gs)!=1:raise RuntimeError('Production generator unavailable')
g=gs[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
backup=ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not backup.exists():backup.write_text(before,encoding='utf-8')
module=json.loads((ROOT/'Config/module.json').read_text('utf-8'));helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for path in sorted(set(helpers['asset_paths'](module))):
    a=u.load_class(None,path) if path.startswith('/Script/') or path.endswith('_C') else u.load_asset(path)
    if not a:raise RuntimeError('Missing dependency '+path)
    assets[a.get_path_name()]=a
catalog=helpers['extend'](catalog,module);g.modify()
g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
packages=[p for p in dirty if 'gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Cannot save generator')
(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Receipts/install.json').write_text(json.dumps(dict(stage='map_saved',module=module['id'],map=TARGET,
    saved_packages=[p.get_name() for p in packages],registration='reserved_fixed_route',unordered_random_pool=False,
    parts=len(module['parts']),lights=len(module['lights']),tests_run=False,editor_opened=False),indent=2),encoding='utf-8')
print('FLUE_GAS_PRODUCTION_SAVED',flush=True)
