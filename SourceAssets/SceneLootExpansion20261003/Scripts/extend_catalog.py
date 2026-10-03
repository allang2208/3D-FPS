"""Add only this batch's bays and restroom prop to the latest catalog."""
import copy,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rules():
    data=json.loads((ROOT/'Config/layout.json').read_text('utf-8-sig'))
    fitted=ROOT.parent/'StationWorkshop20261003/RefineV4';saved=fitted/'Receipts/install.json'
    if saved.exists() and json.loads(saved.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        data=runpy.run_path(str(fitted/'Scripts/fit_rules.py'))['fitted'](data)
    return data
def expand_rules(previous,groups,revision):
    out=copy.deepcopy(previous)
    out['groups']=[g for g in out.get('groups',[]) if not g['id'].startswith('LootExpansion.')]+copy.deepcopy(groups)
    out.update(revision=revision,loot_expansion_revision=1)
    return out
def expand_warehouse(previous):return expand_rules(previous,rules()['warehouse_groups'],2)
def extend(catalog):
    data=rules();out=copy.deepcopy(catalog);modules={m['id']:m for m in out['modules']}
    transfer=modules.get('FreightTransfer_WarehouseLink')
    if transfer:
        base=transfer.get('warehouse_containers',dict(groups=[],outline=data['outline'],preview_seed=data['preview_seed'],rewards_deferred=True))
        transfer['warehouse_containers']=expand_rules(base,data['freight_groups'],1)
    warehouse=modules.get('AbandonedCargoWarehouse')
    if warehouse and 'warehouse_containers' in warehouse:
        warehouse['warehouse_containers']=expand_warehouse(warehouse['warehouse_containers'])
    staff=modules.get('StaffRecreation')
    if staff:
        staff['props']=[p for p in staff.get('props',[]) if p.get('identity')!='staff_activity_restroom']+[copy.deepcopy(data['restroom_chest'])]
    out.update(scene_loot_expansion_revision=1,warehouse_container_revision=2)
    return out
def choose(groups,seed):
    r=random.Random(seed);result=[]
    for group in groups:
        for slot in r.sample(group['slots'],r.randint(*group['pick_count'])):
            result.extend(copy.deepcopy(r.choice(slot['variants'])['containers']))
    return result
def asset_paths(value):
    if isinstance(value,str) and value.startswith('/Game/'):yield value.split('.')[0]
    elif isinstance(value,dict):
        for v in value.values():yield from asset_paths(v)
    elif isinstance(value,list):
        for v in value:yield from asset_paths(v)
