"""Reapply the installed single ward module without resetting other room recipes."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extend(catalog,module=None):
    if module is None:module=json.loads((ROOT/'Config/module.json').read_text(encoding='utf-8'))
    result=copy.deepcopy(catalog);rid=module['id']
    result['modules']=[m for m in result['modules'] if m['id']!=rid]+[module]
    result['room_ids']=list(dict.fromkeys(result['room_ids']+[rid]))
    return result
def asset_paths(module):
    for p in module['parts']:
        yield p['mesh']
        yield from filter(None,p['materials'])
    for light in module['lights']:
        if light.get('light_function'):yield light['light_function']
    yield from module['runtime_assets']
    for p in module['spawn']['pool']:yield p['class']
