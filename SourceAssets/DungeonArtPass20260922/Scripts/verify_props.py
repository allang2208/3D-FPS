"""Independent read-back of the imported props (fresh process, disk state only).

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']
PREP = json.loads((ROOT / 'Receipts' / 'prepare.json').read_text(encoding='utf-8-sig'))

report = {'stage': 'verify_readback', 'content_root': BASE, 'tests_run': False, 'meshes': {}}


def vec(v):
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


for prop in SPEC['props']:
    key = prop['key']
    for output in PREP['props'].get(key, {}).get('outputs', []):
        name = output['mesh_name']
        mesh = u.load_asset(BASE + '/Meshes/' + name)
        if not isinstance(mesh, u.StaticMesh):
            report['meshes'][name] = {'found': False}
            continue
        bounds = mesh.get_bounds()
        slots = []
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            mic = mesh.get_material(index)
            parent = None
            blend = None
            two_sided = None
            if isinstance(mic, u.MaterialInstanceConstant):
                parent_asset = mic.get_editor_property('parent')
                parent = parent_asset.get_path_name().split('.')[0] if parent_asset else None
                if isinstance(parent_asset, u.Material):
                    blend = str(parent_asset.get_editor_property('blend_mode'))
                    two_sided = bool(parent_asset.get_editor_property('two_sided'))
            slots.append({'slot': str(slot.material_slot_name), 'instance': mic.get_path_name().split('.')[0] if mic else None,
                          'instance_type': mic.get_class().get_name() if mic else None,
                          'parent': parent, 'blend_mode': blend, 'two_sided': two_sided})
        body = mesh.get_editor_property('body_setup')
        report['meshes'][name] = {
            'found': True,
            'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                        round(float(bounds.box_extent.z) * 2, 2)],
            'origin_cm': vec(bounds.origin),
            'expected_source_tris': output['tris'],
            'slots': slots,
            'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
            'collision_trace_flag': str(body.get_editor_property('collision_trace_flag')),
        }

textures = u.EditorAssetLibrary.list_assets(BASE + '/Textures', recursive=True, include_folder=False)
report['texture_count'] = len(textures)
(ROOT / 'Receipts' / 'verify.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('ART_PASS_VERIFY ' + json.dumps(report, default=str))
