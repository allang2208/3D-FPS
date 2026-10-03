"""Attach one fixed workshop and its bounded dressing states to the accepted station."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def extend(catalog,rules=None):
    out=copy.deepcopy(catalog);rules=rules or json.loads((ROOT/'Config/workshop.json').read_text('utf8'))
    station=next(m for m in out['modules'] if m['id']=='AbandonedTransitStation')
    station['parts']=[p for p in station['parts'] if not p.get('station_workshop_part')]+copy.deepcopy(rules['fixed_parts'])
    station['lights']=[p for p in station['lights'] if not p.get('station_workshop_light')]+copy.deepcopy(rules['lights'])
    station['runtime_actors']=[p for p in station.get('runtime_actors',[]) if not p.get('station_workshop_actor')]+copy.deepcopy(rules.get('runtime_actors',[]))
    station['props']=[p for p in station.get('props',[]) if not p.get('station_workshop_prop')]+copy.deepcopy(rules.get('props',[]))
    station['runtime_assets']=list(dict.fromkeys(station.get('runtime_assets',[])+list(asset_paths(rules.get('runtime_actors',[])))))
    station['station_workshop']=rules
    out['station_workshop_revision']=rules['revision']
    remap={**rules.get('text_asset_remap',{}),**rules.get('geometry_asset_remap',{})}
    def replace(value):
        if isinstance(value,str):return remap.get(value,value)
        if isinstance(value,list):return [replace(v) for v in value]
        if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
        return value
    if remap:out=replace(out)
    return out

def asset_paths(value):
    if isinstance(value,str) and value.startswith('/Game/'):yield value
    elif isinstance(value,dict):
        for item in value.values():yield from asset_paths(item)
    elif isinstance(value,list):
        for item in value:yield from asset_paths(item)

def preview(rules):
    state=next(v for v in rules['variants'] if v['id']==rules['preview_variant'])
    return copy.deepcopy(rules['fixed_parts']+state['parts']),copy.deepcopy(state['containers'])
