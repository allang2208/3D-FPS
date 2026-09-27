"""Attach post-layout scene recipes. Keep the room pool and route constraints unchanged."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def extend(catalog):
    result=copy.deepcopy(catalog)
    config=json.loads((ROOT/'Config/scene-recipes.json').read_text(encoding='utf-8'))
    for module in result['modules']:
        family=module.get('family_id',module['id'])
        if family in config['families']:
            module['scene_recipes']=copy.deepcopy(config['families'][family])
    result['room_scene_version']=config['version']
    return result
