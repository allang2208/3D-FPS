"""Keep the accepted staff sequence as a fourth eligible theme, never a transition."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog):
    data=json.loads((ROOT/'Config/modules.json').read_text('utf8'));out=copy.deepcopy(catalog)
    modules={m['id']:m for m in out['modules']}
    for m in data['modules']:modules[m['id']]=copy.deepcopy(m)
    out['modules']=list(modules.values())
    out['room_ids']=list(dict.fromkeys(out['room_ids']+data['sequence']))
    rules=out['themed_routes'];rules['routes']=[r for r in rules['routes'] if r['id']!='staff_living']
    rules['routes'].append(dict(id='staff_living',sequence=data['sequence']))
    rules['forward_only']=list(dict.fromkeys(rules['forward_only']+data['sequence']))
    rules.update(theme_candidates=4,selected_routes_per_run=3,version=2)
    out.update(staff_living_revision=7,scene_container_outline=data['container_outline'])
    expansion=ROOT.parents[1]/'SceneLootExpansion20261003';saved=expansion/'Receipts/install.json'
    if saved.exists() and json.loads(saved.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        out=runpy.run_path(str(expansion/'Scripts/extend_catalog.py'))['extend'](out)
    return out

def asset_paths(value):
    if isinstance(value,str) and value.startswith(('/Game/','/Script/')):yield value.split('.')[0] if value.startswith('/Game/') and '.' in value and not value.endswith('_C') else value
    elif isinstance(value,dict):
        for v in value.values():yield from asset_paths(v)
    elif isinstance(value,list):
        for v in value:yield from asset_paths(v)
