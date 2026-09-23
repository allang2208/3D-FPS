"""Independent read-back of the imported statue set (fresh process, disk state only).

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'Config' / 'statues.json').read_text(encoding='utf-8-sig'))
BASE = CFG['content_root']

report = {'stage': 'verify_readback', 'content_root': BASE, 'tests_run': False, 'assets': {}}


def vec3(v):
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


for statue in CFG['statues']:
    key = statue['key']
    mesh_path = BASE + '/Meshes/' + statue['mesh_name']
    mesh = u.load_asset(mesh_path)
    if not isinstance(mesh, u.StaticMesh):
        report['assets'][key] = {'mesh': mesh_path, 'found': False}
        continue
    bounds = mesh.get_bounds()
    body = mesh.get_editor_property('body_setup')
    geom = body.get_editor_property('agg_geom')
    simple = {}
    for prop in ('box_elems', 'convex_elems', 'sphere_elems', 'sphyl_elems'):
        try:
            simple[prop] = len(list(geom.get_editor_property(prop)))
        except Exception as exc:  # noqa: BLE001
            simple[prop] = 'unavailable: %s' % exc
    slot0 = mesh.get_material(0)
    mic = u.load_asset(BASE + '/Materials/MI_' + statue['material_name'][2:])
    tex = u.load_asset(BASE + '/Textures/T_Statue_%s_BaseColor' % key.capitalize())
    report['assets'][key] = {
        'found': True,
        'mesh': mesh_path,
        'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                    round(float(bounds.box_extent.z) * 2, 2)],
        'origin_cm': vec3(bounds.origin),
        'material_slots': len(mesh.get_editor_property('static_materials')),
        'slot0': slot0.get_path_name().split('.')[0] if slot0 else None,
        'material_instance_found': isinstance(mic, u.MaterialInstanceConstant),
        'parent': mic.get_editor_property('parent').get_path_name().split('.')[0]
                  if isinstance(mic, u.MaterialInstanceConstant) and mic.get_editor_property('parent') else None,
        'texture_found': isinstance(tex, u.Texture2D),
        'texture_srgb': bool(tex.get_editor_property('srgb')) if isinstance(tex, u.Texture2D) else None,
        'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
        'collision_trace_flag': str(body.get_editor_property('collision_trace_flag')),
        'simple_collision': simple,
    }

(ROOT / 'Receipts' / 'verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('STATUE_SET_VERIFY ' + json.dumps(report, default=str))
