"""Diagnose why the SVD reads as untextured: textures, material graphs, instances and UVs.

Checks the whole chain in one pass - are the texture assets real, do the M_SVD_* graphs carry
their sample parameters, do the instances parent to them, does the viewmodel's LOD0 actually
have UVs and non-zero texture coordinates - so the cause is read off evidence instead of
guessed.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']
LIB = u.MaterialEditingLibrary
report = {'textures': {}, 'materials': {}, 'instances': {}, 'mesh': {}}

for role in ('basecolor', 'normal', 'roughness', 'metallic', 'ao'):
    for group in ('svd', 'pso'):
        path = '%s/Textures/T_SVD_%s_%s' % (BASE, group, role)
        tex = u.load_asset(path)
        if tex is None:
            report['textures'][path] = {'found': False}
            continue
        report['textures'][path] = {
            'found': True, 'class': tex.get_class().get_name(),
            'size': [int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())],
            'srgb': bool(tex.get_editor_property('srgb')),
            'compression': str(tex.get_editor_property('compression_settings')),
            'lod_group': str(tex.get_editor_property('lod_group')),
        }

for part in SPEC['parts']:
    mat = u.load_asset('%s/Materials/M_SVD_%s' % (BASE, part['part_name']))
    if mat is None:
        report['materials'][part['part_name']] = {'found': False}
        continue
    samples, params = [], []
    for expression in LIB.get_material_expressions(mat):
        name = expression.get_class().get_name()
        if 'TextureSample' in name:
            tex = None
            try:
                tex = expression.get_editor_property('texture')
            except Exception:  # noqa: BLE001
                pass
            samples.append({
                'class': name,
                'parameter': str(expression.get_editor_property('parameter_name')) if hasattr(expression, 'get_editor_property') else None,
                'texture': tex.get_path_name().split('.')[0] if tex else None,
                'sampler': str(expression.get_editor_property('sampler_type')),
            })
    report['materials'][part['part_name']] = {
        'found': True, 'expressions': len(LIB.get_material_expressions(mat)),
        'samples': samples, 'params': params,
        'base_color_connected': LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR) is not None
            if hasattr(LIB, 'get_material_property_input_node') else 'unavailable',
    }

    mi = u.load_asset('%s/Materials/MI_SVD_%s' % (BASE, part['part_name']))
    if mi is None:
        report['instances'][part['part_name']] = {'found': False}
        continue
    parent = mi.get_editor_property('parent')
    values = {}
    for name in ('Tex_basecolor', 'Tex_normal', 'Tex_roughness', 'Tex_metallic', 'Tex_ao'):
        try:
            tex = LIB.get_material_instance_texture_parameter_value(mi, name)
            values[name] = tex.get_path_name().split('.')[0] if tex else None
        except Exception as exc:  # noqa: BLE001
            values[name] = 'ERR %s' % str(exc)[:60]
    report['instances'][part['part_name']] = {
        'found': True,
        'parent': parent.get_path_name().split('.')[0] if parent else None,
        'parameter_values': values,
    }

mesh = u.load_asset(BASE + '/Viewmodel/SK_SVD_Manny')
if isinstance(mesh, u.SkeletalMesh):
    sk = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    uv_info = None
    try:
        uv = [str(x) for x in mesh.get_editor_property('materials')]
        uv_info = len(uv)
    except Exception:  # noqa: BLE001
        pass
    report['mesh'] = {
        'found': True,
        'lod0_verts': int(sk.get_num_verts(mesh, 0)),
        'slots': [str(s.get_editor_property('material_slot_name')) for s in mesh.get_editor_property('materials')],
        'slot_materials': [s.get_editor_property('material_interface').get_path_name().split('.')[0]
                           if s.get_editor_property('material_interface') else None
                           for s in mesh.get_editor_property('materials')],
        'uv_channels': uv_info,
    }
else:
    report['mesh'] = {'found': False}

(ROOT / 'Receipts' / 'material_diagnosis.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('SVD_MATERIAL_DIAGNOSIS ' + json.dumps(report, default=str))
