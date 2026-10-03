"""Production asset registration without violating the required fixed pair."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog,module=None):
    module=module or json.loads((ROOT/'Config/module.json').read_text('utf-8'))
    containers=ROOT.parents[1]/'IncineratorContainers20261003'
    receipt=containers/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        module=runpy.run_path(str(containers/'Scripts/catalog_rules.py'))['extend_module'](module)
    chest=ROOT.parents[1]/'FlueUnderPlatformChest20261003'
    receipt=chest/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        module=runpy.run_path(str(chest/'Scripts/extend_catalog.py'))['extend_module'](module)
    result=copy.deepcopy(catalog);rid=module['id']
    result['modules']=[m for m in result['modules'] if m['id']!=rid]+[module]
    # The current solver has no fixed-sequence contract. Do not expose a free draw.
    result['room_ids']=[x for x in result['room_ids'] if x!=rid]
    return result
def asset_paths(v):
    if isinstance(v,str) and v.startswith(('/Game/','/Script/')):yield v
    elif isinstance(v,dict):
        for x in v.values():yield from asset_paths(x)
    elif isinstance(v,list):
        for x in v:yield from asset_paths(x)
