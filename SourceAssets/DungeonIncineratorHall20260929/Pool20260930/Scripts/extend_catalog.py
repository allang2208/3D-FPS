"""Reapply the accepted incinerator module without regenerating its retired sample."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog,module=None):
    module=module or json.loads((ROOT/'Config/module.json').read_text(encoding='utf-8'))
    result=copy.deepcopy(catalog);rid=module['id']
    result['modules']=[m for m in result['modules'] if m['id']!=rid]+[module]
    result['room_ids']=list(dict.fromkeys(result['room_ids']+[rid]));return result
def asset_paths(value):
    if isinstance(value,str) and value.startswith(('/Game/','/Script/')):yield value
    elif isinstance(value,dict):
        for item in value.values():yield from asset_paths(item)
    elif isinstance(value,list):
        for item in value:yield from asset_paths(item)
