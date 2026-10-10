"""Read only the reported Frost Spirit material and its blade assignments."""
from pathlib import Path
import json
import unreal as u
P = Path(__file__).resolve().parent
ROOT = P.parents[1]
E = u.MaterialEditingLibrary
ASSET = '/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
mat = u.load_asset(ASSET)
if not mat:
    raise RuntimeError('Missing spirit material')
outputs = {}
for key in ['MP_FRONT_MATERIAL', 'MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_WORLD_POSITION_OFFSET']:
    n = E.get_material_property_input_node(mat, getattr(u.MaterialProperty, key))
    outputs[key] = {'node': n.get_name() if n else None,
                    'output': E.get_material_property_input_node_output_name(mat, getattr(u.MaterialProperty, key))}
row = {'asset': ASSET, 'blend_mode': str(mat.get_editor_property('blend_mode')), 'two_sided': mat.get_editor_property('two_sided'),
       'disable_depth_test': mat.get_editor_property('disable_depth_test'), 'outputs': outputs, 'nodes': [], 'blades': []}
for n in E.get_material_expressions(mat):
    info = {'name': n.get_name(), 'class': n.get_class().get_name(),
            'input_names': list(E.get_material_expression_input_names(n)),
            'input_nodes': [x.get_name() if x else None for x in E.get_inputs_for_material_expression(mat, n)]}
    if isinstance(n, u.MaterialExpressionCustom):
        info['code'] = n.get_editor_property('code')
    if isinstance(n, (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter)):
        v = n.get_editor_property('default_value')
        info.update(parameter=str(n.get_editor_property('parameter_name')), value=[v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v)
    if isinstance(n, u.MaterialExpressionTextureObjectParameter):
        info.update(parameter=str(n.get_editor_property('parameter_name')), texture=n.get_editor_property('texture').get_path_name() if n.get_editor_property('texture') else None)
    row['nodes'].append(info)
catalog = json.loads((ROOT/'Content/ColdSteelData/frost-sword-modules.json').read_text(encoding='utf-8'))
for key, spec in catalog['slots']['blade_1'].items():
    mesh = u.load_asset(spec['mesh'])
    row['blades'].append({'option': key, 'path': spec['mesh'], 'exists': bool(mesh),
                         'dimensions': spec.get('rune_dimensions_cm'),
                         'nanite_enabled': mesh.get_editor_property('nanite_settings').enabled if mesh else None,
                         'materials': [{'slot': str(s.material_slot_name), 'path': s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.get_editor_property('static_materials')] if mesh else []})
(P/'state_before.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
print('FROST_SPIRIT_STATE_READ '+json.dumps({'outputs':outputs,'blades':row['blades']}))
