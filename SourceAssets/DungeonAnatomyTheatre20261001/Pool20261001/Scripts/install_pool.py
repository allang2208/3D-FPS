"""Incrementally save the captured theatre in the real generator and author mirror."""
import copy,hashlib,json,runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent;PROJECT=HALL.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
background='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
module=json.loads((ROOT/'Config/module.json').read_text(encoding='utf-8'))
world=u.EditorLoadingAndSavingUtils.load_map(TARGET) if background else u.find_object(None,TARGET+'.L_Dungeon_Randomized')
if not world:raise RuntimeError('Production map not available')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Load the actual production generator before saving')
g=generators[0];before=g.get_editor_property('module_catalog_json');catalog=json.loads(before)
(ROOT/'Backup').mkdir(exist_ok=True)
backup=ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')
if not backup.exists():backup.write_text(before,encoding='utf-8')
spawn=copy.deepcopy(next(m for m in catalog['modules'] if m['id']=='AbandonedDataArchive')['spawn'])
spawn.update(source='DungeonAnatomyTheatre20261001',count=[4,6],anchor_roles=['theatre_combat'],
    theme='abandoned_anatomy_theatre',sealed_encounter=True)
module['spawn']=spawn
helpers=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
module['runtime_assets']=sorted(set(helpers['asset_paths'](module['runtime_actors'])))
hospital=PROJECT/'SourceAssets/HospitalContainers20261003'
hospital_receipt=hospital/'Receipts/assets.json'
if hospital_receipt.exists() and json.loads(hospital_receipt.read_text('utf8')).get('stage')=='assets_saved':
    module=runpy.run_path(str(hospital/'Scripts/catalog_rules.py'))['extend_module'](module)
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
for item in sorted(set(helpers['asset_paths'](module))):
    asset=u.load_class(None,item) if item.startswith('/Script/') or item.endswith('_C') else u.load_asset(item)
    if not asset:raise RuntimeError('Missing dependency '+item)
    assets[asset.get_path_name()]=asset
catalog=helpers['extend'](catalog,module)
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False));g.set_editor_property('module_assets',list(assets.values()))
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
packages=[p for p in dirty if 'gamemaps/l_dungeon_randomized' in p.get_name().lower()]
if not packages or not u.EditorLoadingAndSavingUtils.save_packages(packages,False):raise RuntimeError('Production generator save failed')
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
write(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json',catalog)
write(ROOT/'Config/module.json',module)
write(ROOT/'Receipts/install.json',dict(stage='map_saved',map=TARGET,module=module['id'],room_ids=catalog['room_ids'],
    saved_packages=[p.get_name() for p in packages],parts=len(module['parts']),lights=len(module['lights']),
    runtime_actors=len(module['runtime_actors']),anchors=len(module['anchors']),selection=module['selection'],
    spawn_count=spawn['count'],blood_decals=3,sample_port_caps_included=False,tests_run=False,rendered=False))
print('ANATOMY_THEATRE_POOL_MAP_SAVED '+TARGET,flush=True)
