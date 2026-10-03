"""Scoped hospital changes; shared seeded selection already supports these groups."""
import copy
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def rules():
    data=json.loads((ROOT/'Config/layout.json').read_text('utf8'))
    office=ROOT.parent/'HospitalDoctorOffice20261003/Receipts/assets.json'
    if office.exists() and json.loads(office.read_text('utf8')).get('stage')=='assets_saved':
        data['count_ranges']['AbandonedIsolationWard']=[11,12]
    return data


def paths(value):
    if isinstance(value,str) and value.startswith('/Game/'):
        yield value.split('.')[0]
    elif isinstance(value,dict):
        for item in value.values():yield from paths(item)
    elif isinstance(value,list):
        for item in value:yield from paths(item)


def extend_module(module,data=None):
    data=data or rules();result=copy.deepcopy(module);identity=result['id']
    if identity not in data['groups']:return result
    previous=result.get('warehouse_containers',{})
    config=copy.deepcopy(previous)
    config['groups']=[g for g in previous.get('groups',[]) if not g['id'].startswith('Hospital.')]+copy.deepcopy(data['groups'][identity])
    config.update(outline=data['outline'],preview_seed=data['preview_seed'],rewards_deferred=True)
    result['warehouse_containers']=config
    result['hospital_container_revision']=data['revision']
    result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+list(paths(config))+list(paths(data['bedside']))))
    if identity=='AbandonedIsolationWard':
        old_reserve=result.get('hospital_container_reservations',[])
        for actor in result.get('runtime_actors',[]):
            if actor['type']!='beds':continue
            actor['room_props']=[p for p in actor.get('room_props',[]) if p['id']!='MedicalCart']
            actor['keep_clear']=[b for b in actor.get('keep_clear',[]) if b not in old_reserve]+copy.deepcopy(data['ward_cart_reservations'])
            actor['bedside_containers']=copy.deepcopy(data['bedside'])
        result['hospital_container_reservations']=copy.deepcopy(data['ward_cart_reservations'])
    polish=ROOT.parent/'HospitalPolish20261003'
    receipt=polish/'Receipts/assets.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='assets_saved':
        import runpy
        result=runpy.run_path(str(polish/'Scripts/fixture_rules.py'))['extend_module'](result)
    office=ROOT.parent/'HospitalDoctorOffice20261003'
    receipt=office/'Receipts/assets.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='assets_saved':
        import runpy
        result=runpy.run_path(str(office/'Scripts/office_rules.py'))['extend_module'](result)
    return result


def extend(catalog):
    result=copy.deepcopy(catalog);data=rules()
    result['modules']=[extend_module(m,data) for m in result['modules']]
    result['hospital_container_revision']=data['revision']
    return result


def choose(groups,seed):
    rng=random.Random(seed);selected=[]
    for group in groups:
        for item in rng.sample(group['slots'],rng.randint(*group['pick_count'])):
            selected.extend(copy.deepcopy(rng.choice(item['variants'])['containers']))
    return selected
