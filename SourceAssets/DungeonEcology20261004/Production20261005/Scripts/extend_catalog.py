"""Apply only the accepted ecology theme to the current production catalog."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parents[1]
REVISION='ecology_production_v1_20261005'
SEQUENCE=['EcoNursery','EcoHydroponics','EcoBiosphere']

def asset_paths(value):
    if isinstance(value,str) and value.startswith(('/Game/','/Script/')):
        yield value
    elif isinstance(value,dict):
        for v in value.values():yield from asset_paths(v)
    elif isinstance(value,list):
        for v in value:yield from asset_paths(v)

def extend(catalog):
    data=json.loads((ROOT/'Config/modules.json').read_text('utf8'))
    result=copy.deepcopy(catalog)
    modules={m['id']:m for m in result['modules']}
    for module in data['modules']:modules[module['id']]=copy.deepcopy(module)
    result['modules']=list(modules.values())
    # Combat eligibility is needed by the themed slot resolver. A route-only
    # selection and non-transition family keep these rooms out of ordinary draws.
    result['room_ids']=list(dict.fromkeys(result['room_ids']+SEQUENCE))
    rules=result['themed_routes']
    rules['routes']=[r for r in rules['routes'] if r['id']!='ecology']
    rules['routes'].append(dict(id='ecology',sequence=SEQUENCE))
    rules['forward_only']=list(dict.fromkeys(rules['forward_only']+SEQUENCE))
    rules['transition_families']=[f for f in rules['transition_families'] if f not in SEQUENCE]
    rules.update(theme_candidates=len(rules['routes']),selected_routes_per_run=3)
    result['ecology_theme_revision']=REVISION
    return result
