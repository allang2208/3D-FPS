"""Reapply the accepted treatment core without changing other route rules."""
import copy
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release():
    return json.loads((ROOT / 'Config/release.json').read_text('utf-8'))


def asset_paths(value):
    if isinstance(value, str) and value.startswith('/Game/'):
        yield value.split('.')[0]
    elif isinstance(value, dict):
        for item in value.values():
            yield from asset_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from asset_paths(item)


def extend(catalog):
    data = release()
    result = copy.deepcopy(catalog)
    for key in ('container_source', 'chest_source'):
        rules = runpy.run_path(str(ROOT.parent / data[key] / 'Scripts/extend_catalog.py'))
        result = rules['extend'](result)
    # Existing transitions, the other themed cores, gates and encounter data
    # remain in the current catalog. The treatment core stays indivisible.
    routes = result['themed_routes']['routes']
    target = next(route for route in routes if route['id'] == data['route_id'])
    target['sequence'] = list(data['sequence'])
    result['treatment_theme_revision'] = data['revision']
    return result
