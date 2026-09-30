"""Read-only: dump MF_PhongToMetalRoughness (expressions, properties, input edges).

M4's polymer look in game is this conversion's output, not the author's PBR maps.
Writes inspect/phong_function.json. Nothing is modified or saved.
"""
import json
import unreal as u
from pathlib import Path

O = Path(__file__).parent
L = u.MaterialEditingLibrary
fn = u.load_asset('/InterchangeAssets/Functions/MF_PhongToMetalRoughness')
anchor = u.load_asset('/Game/Weapons/M4InfimaV3/Grip_Default_001').get_base_material()
KEYS = ['input_name', 'output_name', 'const_a', 'const_b', 'const_exponent', 'min_default', 'max_default',
        'parameter_name', 'default_value', 'preview_value', 'r', 'constant', 'input_type', 'sort_priority',
        'description', 'code']
nodes = []
for expr in L.get_material_function_expressions(fn):
    item = {'name': expr.get_name(), 'class': expr.get_class().get_name()}
    for key in KEYS:
        try:
            value = expr.get_editor_property(key)
        except Exception:
            continue
        if isinstance(value, (u.LinearColor, u.Vector4)):
            value = [value.r, value.g, value.b, value.a] if isinstance(value, u.LinearColor) else [value.x, value.y, value.z, value.w]
        elif not isinstance(value, (int, float, str, bool)):
            value = str(value)
        item[key] = value
    try:
        inputs = L.get_inputs_for_material_expression(anchor, expr)
        names = [str(n) for n in L.get_material_expression_input_names(expr)]
        item['inputs'] = [[names[i] if i < len(names) else i, s.get_name(),
                           str(L.get_input_node_output_name_for_material_expression(expr, s))]
                          for i, s in enumerate(inputs) if s]
    except Exception as exc:
        item['inputs_error'] = str(exc)[:160]
    nodes.append(item)
(O / 'inspect' / 'phong_function.json').write_text(json.dumps(nodes, indent=1), encoding='utf-8')
print('WEAPON_SURFACE_PHONG', len(nodes), flush=True)
