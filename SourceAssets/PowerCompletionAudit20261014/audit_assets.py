"""Read saved power modules/assets without changing maps, packages or player saves."""
from pathlib import Path
from datetime import datetime, timezone
import json
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
checks=[]
def require(ok, label, detail=None):
    checks.append(dict(pass_=bool(ok), label=label, detail=detail))
def read(path): return json.loads(path.read_text('utf-8-sig'))
data=read(PROJECT/'Content/ColdSteelData/scene_search_loot.json')
items=read(PROJECT/'Content/ColdSteelData/items.json')
pools={p['id']:p for p in data['pools']}
bindings={b['container_id']:b['pool'] for b in data['bindings']}
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
require(len(generators)==1,'one production dungeon generator')
catalog=json.loads(generators[0].get_editor_property('module_catalog_json'))
modules=[m for m in catalog['modules'] if m['id'] in ['SwitchgearGallery','GeneratorHall','AccumulatorControl']]
require(len(modules)==3,'all three power modules saved')
containers=[]
for module in modules:
    candidates=[a for a in module.get('runtime_actors',[]) if a.get('type')=='scene_container']
    require(len(candidates)=={'SwitchgearGallery':4,'GeneratorHall':3,'AccumulatorControl':7}[module['id']],module['id']+' container count',len(candidates))
    for actor in candidates:
        identity=actor['container_id']; profile=bindings.get(identity)
        require(profile in pools,identity+' loot bound',profile)
        for kind in ['body','door']:
            asset=u.load_asset(actor[kind]); require(asset is not None,identity+' '+kind+' resolves')
            if '.MaintenanceToolbox.' in identity and asset:
                bounds=asset.get_bounding_box()
                actor[kind+'_bounds']=[str(bounds.min),str(bounds.max)]
        containers.append(dict(module=module['id'],id=identity,pool=profile,recipe=actor))
require(len({a['id'] for a in containers})==14,'14 unique searchable container identities')
for row in containers:
    if row['pool'] not in pools:continue
    pool=pools[row['pool']]
    require(sum(pool['count_weights'])==100,row['id']+' valid quantity weights')
    for entry in pool['entries']:
        require(entry['id'] in items,row['id']+' item definition '+entry['id'])
new_ids=['search_industrial_fuse_set','search_power_control_module','search_energy_storage_cell']
assets=[]
for identity,grid in zip(new_ids,[(1,1),(2,1),(1,2)]):
    item=items[identity]
    require((item['grid_w'],item['grid_h'])==grid,identity+' inventory footprint')
    require((PROJECT/'Content/ColdSteelData'/item['ue_icon']).is_file(),identity+' inventory icon exists')
    mesh=u.load_asset(item['world_mesh']); require(mesh is not None,identity+' pickup mesh resolves')
    if mesh:
        mats=mesh.get_editor_property('static_materials')
        require(bool(mats) and all(m.material_interface is not None for m in mats),identity+' material slots resolve')
        assets.append(dict(id=identity,mesh=mesh.get_path_name(),bounds=str(mesh.get_bounding_box()),materials=[m.material_interface.get_path_name() for m in mats]))
classes=[]
for path in ['/Game/Monsters/FacelessResearcher/BP_FacelessResearcher.BP_FacelessResearcher_C',
             '/Game/Monsters/CargoTechnician/BP_CargoTechnician.BP_CargoTechnician_C',
             '/Script/FPSGAME.HangingBellM09',
             '/Game/Monsters/VortexCofferM25/BP_VortexCofferM25.BP_VortexCofferM25_C']:
    cls=u.load_class(None,path); require(cls is not None,path+' resolves')
    if cls:
        cdo=u.get_default_object(cls)
        require(cdo.get_editor_property('replicates'),path+' actor replicates')
        classes.append(dict(path=path,replicates=cdo.get_editor_property('replicates'),rank=str(cdo.get_editor_property('rank'))))
report=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),checks=checks,
    failures=[r for r in checks if not r['pass_']],modules=modules,containers=containers,
    assets=assets,monster_classes=classes,assets_saved=False,game_started=False,dual_client_tested=False)
(ROOT/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_ASSET_AUDIT checks=%d failures=%d'%(len(checks),len(report['failures'])))
if report['failures']:raise RuntimeError('Power asset audit failed; see assets.json')
