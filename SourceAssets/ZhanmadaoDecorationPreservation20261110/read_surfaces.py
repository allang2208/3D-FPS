"""Inventory every live Zhanmadao blade slot and its temporal material graph."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
catalog = json.loads((ROOT / 'Content/ColdSteelData/zhanmadao-modules.json').read_text(encoding='utf-8-sig'))
temporal = json.loads((ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
result = {'blades': {}, 'materials': {}}
for choice, spec in catalog['slots']['blade_1'].items():
    mesh = u.load_asset(spec['mesh'])
    if not mesh:
        raise RuntimeError('Missing blade ' + choice)
    slots = []
    for slot in mesh.static_materials:
        name = str(slot.material_slot_name)
        native = slot.material_interface
        path = spec.get('materials', {}).get(name, native.get_path_name() if native else '')
        slots.append({'slot': name, 'material': path, 'temporal': temporal.get(path)})
        for source in [path, temporal.get(path)]:
            if not source or source in result['materials']:
                continue
            material = u.load_asset(source)
            if not material:
                raise RuntimeError('Missing material ' + source)
            nodes = []
            for node in L.get_material_expressions(material):
                row = {'name': node.get_name(), 'class': node.get_class().get_name(), 'desc': str(node.get_editor_property('desc'))}
                if isinstance(node, u.MaterialExpressionCustom):
                    row['code'] = str(node.get_editor_property('code'))
                if isinstance(node, u.MaterialExpressionTextureSample):
                    texture = node.get_editor_property('texture')
                    row['texture'] = texture.get_path_name() if texture else None
                if isinstance(node, u.MaterialExpressionConstant):
                    row['value'] = node.get_editor_property('r')
                row['inputs'] = {str(name): inp.get_name() if inp else None for name, inp in zip(
                    L.get_material_expression_input_names(node), L.get_inputs_for_material_expression(material, node))}
                nodes.append(row)
            result['materials'][source] = nodes
    result['blades'][choice] = {'mesh': spec['mesh'], 'slots': slots}
(P / 'surface-inputs.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('ZHANMADAO_SURFACE_INVENTORY', len(result['blades']), 'blades', len(result['materials']), 'materials')
