"""Independent read-back of the imported SVD (fresh process, disk state only).

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']

report = {'stage': 'verify_readback', 'content_root': BASE, 'tests_run': False, 'parts': {}, 'textures': {}}


def vec(v):
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


for part in SPEC['parts']:
    name = part['mesh_name']
    mesh = u.load_asset(BASE + '/Meshes/' + name)
    if not isinstance(mesh, u.StaticMesh):
        report['parts'][name] = {'found': False}
        continue
    bounds = mesh.get_bounds()
    mic = mesh.get_material(0)
    parent = None
    if isinstance(mic, u.MaterialInstanceConstant):
        parent_asset = mic.get_editor_property('parent')
        parent = parent_asset.get_path_name().split('.')[0] if parent_asset else None
    body = mesh.get_editor_property('body_setup')
    report['parts'][name] = {
        'found': True,
        'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                    round(float(bounds.box_extent.z) * 2, 2)],
        'origin_cm': vec(bounds.origin),
        'slot0_name': str(mesh.get_editor_property('static_materials')[0].material_slot_name),
        'slot0_instance': mic.get_path_name().split('.')[0] if mic else None,
        'instance_parent': parent,
        'expected_parent': BASE + '/Materials/M_SVD_' + part['key'].capitalize(),
        'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
        'collision_trace_flag': str(body.get_editor_property('collision_trace_flag')),
        'source_tris': part['tris'],
    }

manifest = json.loads((ROOT / 'Receipts' / 'textures.json').read_text(encoding='utf-8-sig'))
for entry in manifest:
    if entry.get('missing'):
        report['textures'][entry['role']] = 'MISSING'
        continue
    tex = u.load_asset(BASE + '/Textures/' + entry['asset_name'])
    report['textures'][entry['asset_name']] = {
        'found': isinstance(tex, u.Texture2D),
        'srgb': bool(tex.get_editor_property('srgb')) if isinstance(tex, u.Texture2D) else None,
        'compression': str(tex.get_editor_property('compression_settings')) if isinstance(tex, u.Texture2D) else None,
        'flip_green': bool(tex.get_editor_property('flip_green_channel')) if isinstance(tex, u.Texture2D) else None,
        'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()] if isinstance(tex, u.Texture2D) else None,
    }

(ROOT / 'Receipts' / 'verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('SVD_VERIFY ' + json.dumps(report, default=str))
