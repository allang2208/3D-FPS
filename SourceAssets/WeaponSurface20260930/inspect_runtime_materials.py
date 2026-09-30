"""Read-only: dump the runtime material graphs of the reference guns and A762.

Runs inside the editor (project bridge) or a commandlet. Writes
inspect/runtime_materials.json next to this file. No asset is modified or saved.
"""
import json
import unreal as u
from pathlib import Path

O = Path(__file__).parent
OUT = O / 'inspect' / 'runtime_materials.json'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary

MESHES = {
    'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    'AKM': '/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
    'HK416': '/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny',
    'A762': '/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
}
PROPS = ['MP_BASE_COLOR', 'MP_METALLIC', 'MP_SPECULAR', 'MP_ROUGHNESS', 'MP_NORMAL',
         'MP_AMBIENT_OCCLUSION', 'MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_OPACITY_MASK']


def prop(obj, name, default=None):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return default


def texture_info(tex):
    if not tex:
        return None
    data = prop(tex, 'asset_import_data')
    source = None
    try:
        source = data.get_first_filename() if data else None
    except Exception:
        pass
    return {
        'path': tex.get_path_name(),
        'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()] if hasattr(tex, 'blueprint_get_size_x') else None,
        'srgb': bool(prop(tex, 'srgb', False)),
        'compression': str(prop(tex, 'compression_settings')),
        'source_file': source,
    }


def expr_id(expr):
    return expr.get_name() if expr else None


def describe_expr(mat, expr, function=False):
    item = {'name': expr.get_name(), 'class': expr.get_class().get_name()}
    for key in ['parameter_name', 'description', 'desc', 'const_a', 'const_b', 'r', 'constant', 'default_value',
                'coordinate_index', 'sampler_type', 'channel', 'exponent']:
        value = prop(expr, key)
        if value is None:
            continue
        if isinstance(value, u.LinearColor):
            value = [value.r, value.g, value.b, value.a]
        elif not isinstance(value, (int, float, str, bool)):
            value = str(value)
        if value not in ('', 'None'):
            item[key] = value
    tex = prop(expr, 'texture')
    if tex:
        item['texture'] = tex.get_path_name()
    fn = prop(expr, 'material_function')
    if fn:
        item['function'] = fn.get_path_name()
    code = prop(expr, 'code')
    if code:
        item['code'] = str(code)[:1600]
    if not function:
        try:
            inputs = L.get_inputs_for_material_expression(mat, expr)
            names = []
            for i, src in enumerate(inputs):
                if src:
                    out = ''
                    try:
                        out = str(L.get_input_node_output_name_for_material_expression(expr, src))
                    except Exception:
                        pass
                    names.append([i, src.get_name(), out])
            if names:
                item['inputs'] = names
        except Exception as exc:
            item['inputs_error'] = str(exc)[:120]
    return item


def describe_material(mi):
    base = mi.get_base_material()
    chain = []
    cursor = mi
    while cursor is not None and cursor != base:
        chain.append(cursor.get_path_name())
        cursor = prop(cursor, 'parent')
    info = {
        'path': mi.get_path_name(), 'class': mi.get_class().get_name(), 'chain': chain,
        'base': base.get_path_name() if base else None,
    }
    if not base:
        return info
    info['blend_mode'] = str(prop(base, 'blend_mode'))
    info['shading_model'] = str(prop(base, 'shading_model'))
    info['two_sided'] = bool(prop(base, 'two_sided', False))
    info['used_with_skeletal_mesh'] = bool(prop(base, 'used_with_skeletal_mesh', False))
    info['tangent_space_normal'] = bool(prop(base, 'tangent_space_normal', True))
    params = {}
    for kind in ['scalar', 'vector', 'texture', 'static_switch']:
        getter = getattr(L, 'get_' + kind + '_parameter_names', None)
        if not getter:
            continue
        params[kind] = {}
        for name in getter(base):
            try:
                if isinstance(mi, u.MaterialInstance):
                    value = getattr(L, 'get_material_instance_' + kind + '_parameter_value')(mi, name)
                else:
                    value = getattr(L, 'get_material_default_' + kind + '_parameter_value')(base, name)
            except Exception as exc:
                value = 'ERR ' + str(exc)[:80]
            if kind == 'texture':
                value = texture_info(value)
            elif isinstance(value, u.LinearColor):
                value = [value.r, value.g, value.b, value.a]
            params[kind][str(name)] = value
    info['parameters'] = params
    outputs = {}
    for name in PROPS:
        try:
            node = L.get_material_property_input_node(base, getattr(u.MaterialProperty, name))
            if node:
                pin = ''
                try:
                    pin = str(L.get_material_property_input_node_output_name(base, getattr(u.MaterialProperty, name)))
                except Exception:
                    pass
                outputs[name] = [node.get_name(), pin]
        except Exception:
            pass
    info['outputs'] = outputs
    exprs = list(L.get_material_expressions(base))
    info['expression_count'] = len(exprs)
    info['expressions'] = [describe_expr(base, e) for e in exprs[:260]]
    try:
        info['used_textures'] = [texture_info(t) for t in L.get_used_textures(base)]
    except Exception:
        info['used_textures'] = []
    functions = {}
    for e in exprs:
        fn = prop(e, 'material_function')
        if fn and fn.get_path_name() not in functions:
            try:
                fexprs = list(L.get_material_function_expressions(fn))
                functions[fn.get_path_name()] = [describe_expr(fn, x, True) for x in fexprs[:200]]
            except Exception as exc:
                functions[fn.get_path_name()] = 'ERR ' + str(exc)[:120]
    info['functions'] = functions
    return info


report = {'meshes': {}, 'materials': {}, 'modified': False}
for key, path in MESHES.items():
    mesh = u.load_asset(path)
    if not mesh:
        report['meshes'][key] = {'path': path, 'error': 'missing'}
        continue
    slots = mesh.get_editor_property('materials')
    entry = {'path': mesh.get_path_name(), 'slots': []}
    for s in slots:
        m = s.material_interface
        entry['slots'].append({'slot': str(s.material_slot_name), 'material': m.get_path_name() if m else None})
        if m and m.get_path_name() not in report['materials']:
            report['materials'][m.get_path_name()] = describe_material(m)
    try:
        entry['bounds'] = str(mesh.get_bounds())
    except Exception:
        pass
    report['meshes'][key] = entry

wet_tables = ['/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials', '/Game/Weather/NaturalV2/DA_WeatherPresentation']
report['wet_tables'] = {}
for tpath in wet_tables:
    table = u.load_asset(tpath)
    if not table:
        continue
    mapping = prop(table, 'wet_materials') or {}
    report['wet_tables'][tpath] = {str(k): (v.get_path_name() if v else None) for k, v in mapping.items()}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
print('WEAPON_SURFACE_INSPECT', json.dumps({k: len(v.get('slots', [])) for k, v in report['meshes'].items()}),
      'materials', len(report['materials']), flush=True)
