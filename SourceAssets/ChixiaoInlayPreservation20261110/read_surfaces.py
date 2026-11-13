"""Read the two active Chixiao surface graphs for the reported missing inlay."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
L = u.MaterialEditingLibrary
BASE = '/Game/Weapons/Zhanmadao20261018/ChixiaoBladeV1/Materials/M_TangDaoBladeRuneSurface_Zhanmadao_chixiao_V1'
paths = [BASE, BASE + '_Whirlwind']
result = []
for path in paths:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing ' + path)
    nodes = []
    for node in L.get_material_expressions(material):
        entry = {'name': node.get_name(), 'class': node.get_class().get_name(), 'desc': str(node.get_editor_property('desc'))}
        if isinstance(node, u.MaterialExpressionCustom):
            entry['code'] = str(node.get_editor_property('code'))
        if isinstance(node, u.MaterialExpressionTextureSample):
            texture = node.get_editor_property('texture')
            entry['texture'] = texture.get_path_name() if texture else None
        if isinstance(node, u.MaterialExpressionConstant):
            entry['value'] = node.get_editor_property('r')
        entry['inputs'] = {str(name): source.get_name() if source else None for name, source in zip(
            L.get_material_expression_input_names(node), L.get_inputs_for_material_expression(material, node))}
        nodes.append(entry)
    result.append({'asset': path, 'nodes': nodes})
(P / 'surface-inputs.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CHIXIAO_SURFACE_INPUTS_SAVED', [(row['asset'], len(row['nodes'])) for row in result])
