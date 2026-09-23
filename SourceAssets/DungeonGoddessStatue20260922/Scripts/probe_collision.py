"""Probe the statue's simple collision primitives.

Project history: generated sphere/sphyl primitives on curved meshes produced shapes
that spanned floor-to-ceiling and blocked interiors. The statue is placed inside a
4x5 m cavity, so the simple collision element types and their sizes must be known.

Run headless:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
MESH = '/Game/Dungeons/GoddessStatue20260922/Meshes/SM_GoddessStatue_Diana'

mesh = u.load_asset(MESH)
if not isinstance(mesh, u.StaticMesh):
    raise RuntimeError('mesh missing: %s' % MESH)

body = mesh.get_editor_property('body_setup')
geom = body.get_editor_property('agg_geom')

report = {'mesh': MESH, 'collision_trace_flag': str(body.get_editor_property('collision_trace_flag'))}
ELEMENT_PROPS = ('box_elems', 'convex_elems', 'sphere_elems', 'sphyl_elems', 'taper_elems')
for name in ELEMENT_PROPS:
    try:
        elems = list(geom.get_editor_property(name))
    except Exception as exc:  # noqa: BLE001 - property set differs between engine versions
        report[name] = {'count': 'unavailable', 'error': str(exc)}
        continue
    entry = {'count': len(elems)}
    if name == 'box_elems' and elems:
        e = elems[0]
        entry['sample'] = {
            'center': [round(float(e.center.x), 2), round(float(e.center.y), 2), round(float(e.center.z), 2)],
            'x': round(float(e.x), 2), 'y': round(float(e.y), 2), 'z': round(float(e.z), 2),
        }
    if name == 'sphere_elems' and elems:
        entry['sample'] = {'radius': round(float(elems[0].radius), 2)}
    if name == 'sphyl_elems' and elems:
        entry['sample'] = {'radius': round(float(elems[0].radius), 2), 'length': round(float(elems[0].length), 2)}
    if name == 'convex_elems' and elems:
        entry['sample'] = {'element_count': len(elems), 'note': 'convex hull of the scanned surface'}
    report[name] = entry

bounds = mesh.get_bounds()
report['mesh_size_cm'] = [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                          round(float(bounds.box_extent.z) * 2, 2)]
report['simple_total'] = sum(v['count'] for k, v in report.items()
                             if k in ELEMENT_PROPS and isinstance(v, dict) and isinstance(v.get('count'), int))
(ROOT / 'Receipts' / 'collision_probe.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('GODDESS_STATUE_COLLISION', json.dumps(report, default=str))
