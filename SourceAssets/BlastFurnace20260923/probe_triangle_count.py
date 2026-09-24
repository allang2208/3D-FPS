"""Probe why the imported triangle count differs from the exported one.

Compares the blast furnace against an already-accepted Nanite prop (the square
altar) whose Blender triangle count is known, so the reading can be attributed
to the asset or to the way ``get_num_triangles`` reports a Nanite mesh.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
TARGETS = {
    'blast_furnace': '/Game/Props/BlastFurnace20260923/SM_BlastFurnace',
    'square_altar': '/Game/Props/SquareAltar20260922/SM_SquareAltar',
}


def describe(mesh):
    info = {}
    nanite = mesh.get_editor_property('nanite_settings')
    info['nanite'] = bool(nanite.enabled)
    for prop in ('fallback_percent_triangles', 'fallback_relative_error',
                 'keep_percent_triangles', 'trim_relative_error', 'position_precision'):
        try:
            info[prop] = getattr(nanite, prop)
        except AttributeError:
            info[prop] = 'unavailable'
    for name, args in (('get_num_lods', ()), ('get_num_triangles', (0,)),
                       ('get_num_vertices', (0,)), ('get_num_uv_channels', (0,))):
        function = getattr(mesh, name, None)
        if function is None:
            info[name] = 'missing'
            continue
        try:
            info[name] = function(*args)
        except Exception as error:  # noqa: BLE001
            info[name] = 'unavailable: %s' % error
    try:
        info['lod_screen_sizes'] = [mesh.get_editor_property('lod_group') and None]
    except Exception:  # noqa: BLE001
        pass
    return info


report = {}
for key, path in TARGETS.items():
    mesh = u.load_asset(path)
    report[key] = describe(mesh) if mesh else 'missing'

(HERE / 'triangle_probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('TRIANGLE_PROBE ' + json.dumps(report, ensure_ascii=False), flush=True)
