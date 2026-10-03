"""Append exactly one accepted treasure chest without replacing unrelated fields."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def rules():return json.loads((ROOT/'Config/chest.json').read_text('utf8'))

def asset_paths(value):
    if isinstance(value,str) and value.startswith('/Game/'):yield value.split('.')[0]
    elif isinstance(value,dict):
        for item in value.values():yield from asset_paths(item)
    elif isinstance(value,list):
        for item in value:yield from asset_paths(item)

def extend_module(module):
    result=copy.deepcopy(module);data=rules()
    if result['id']!=data['module']:return result
    chest=copy.deepcopy(data['chest'])
    result['props']=[p for p in result.get('props',[]) if p.get('identity')!=chest['identity']]+[chest]
    result['runtime_assets']=list(dict.fromkeys(result.get('runtime_assets',[])+list(asset_paths(chest))))
    result['flue_under_platform_chest_revision']=data['revision']
    return result

def extend(catalog):
    result=copy.deepcopy(catalog)
    result['modules']=[extend_module(m) for m in result['modules']]
    return result
