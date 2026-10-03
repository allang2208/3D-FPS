"""Scoped treatment groups, seeded preview selection and rebuild integration."""
import copy
import hashlib
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFIX='Treatment.'


def read_layout():return json.loads((ROOT/'Config/layout.json').read_text('utf8'))


def paths(value):
    if isinstance(value,str) and value.startswith('/Game/'):yield value.split('.')[0]
    elif isinstance(value,dict):
        for item in value.values():yield from paths(item)
    elif isinstance(value,list):
        for item in value:yield from paths(item)


def geometry_key(module):
    parts=[{k:p.get(k) for k in ('mesh','position','yaw','scale')} for p in module['parts']
        if not p.get('treatment_container_fixed')]
    data=dict(parts=parts,walk_mask=module.get('walk_mask',[]),ports=module['ports'])
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def extend_module(module,layout=None):
    layout=layout or read_layout();result=copy.deepcopy(module);identity=result['id']
    if identity not in layout['groups']:return result
    previous=result.get('warehouse_containers',{})
    config=copy.deepcopy(previous)
    config['groups']=[g for g in previous.get('groups',[]) if not g['id'].startswith(PREFIX)]+copy.deepcopy(layout['groups'][identity])
    config.update(outline=layout['outline'],preview_seed=layout['preview_seed'],rewards_deferred=True)
    result['warehouse_containers']=config
    result['parts']=[p for p in result['parts'] if not p.get('treatment_container_fixed')]+copy.deepcopy(layout['fixed_parts'][identity])
    result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+list(paths(config))+list(paths(layout['fixed_parts'][identity]))))
    result['treatment_container_revision']=layout['revision']
    return result


def extend(catalog):
    result=copy.deepcopy(catalog);layout=read_layout()
    result['modules']=[extend_module(m,layout) for m in result['modules']]
    result['treatment_container_revision']=layout['revision']
    return result


def choose(groups,seed):
    # Preview is intentionally fixed. Runtime uses the project's seeded FRandomStream.
    rng=random.Random(seed);selected=[]
    for group in groups:
        for slot in rng.sample(group['slots'],rng.randint(*group['pick_count'])):
            selected.extend(copy.deepcopy(rng.choice(slot['variants'])['containers']))
    return selected
