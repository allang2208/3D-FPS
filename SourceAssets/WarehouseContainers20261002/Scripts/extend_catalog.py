import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog):
    out=copy.deepcopy(catalog);rules=json.loads((ROOT/'Config/containers.json').read_text('utf8'))
    module=next(m for m in out['modules'] if m['id']=='AbandonedCargoWarehouse')
    module['warehouse_containers']=rules
    # Author geometry index is stable: flag a cargo part without moving/replacing other parts.
    source=json.loads((ROOT.parent/'DungeonCargoWarehouse20261001/Config/room.json').read_text('utf8'))
    slots={s['id'] for g in rules['groups'] for s in g['slots']}
    for p in module['parts']:
        if 'SM_Facility_CargoStack' not in p['mesh']:continue
        for c in source['reused_parts']:
            if c['id'] not in slots:continue
            xyz=[c['position'][0]*100,-c['position'][1]*100,c['position'][2]*100]
            if max(abs(p['position'][i]-xyz[i]) for i in range(3))<.1:p['container_replace_slot']=c['id'];break
    out['warehouse_container_revision']=1
    text_refine=ROOT.parent/'StationWorkshop20261003/RefineV2'
    receipt=text_refine/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':
        remap=json.loads((text_refine/'Config/text-asset-remap.json').read_text('utf8'))
        def replace(value):
            if isinstance(value,str):return remap.get(value,value)
            if isinstance(value,list):return [replace(v) for v in value]
            if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
            return value
        out=replace(out)
    expansion=ROOT.parent/'SceneLootExpansion20261003'
    saved=expansion/'Receipts/install.json'
    if saved.exists() and json.loads(saved.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        out=runpy.run_path(str(expansion/'Scripts/extend_catalog.py'))['extend'](out)
    return out

def choose_preview(rules):
    import random
    randomizer=random.Random(rules['preview_seed']);replaced=[];containers=[]
    for group in rules['groups']:
        count=randomizer.randint(*group['pick_count']);slots=randomizer.sample(group['slots'],count)
        bag=[]
        for slot in slots:
            if not bag:bag=list(range(len(slot['variants'])));randomizer.shuffle(bag)
            containers.extend(copy.deepcopy(slot['variants'][bag.pop()]['containers']));replaced.append(slot['id'])
    return replaced,containers
