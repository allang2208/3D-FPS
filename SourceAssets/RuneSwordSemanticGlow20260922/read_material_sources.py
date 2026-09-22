"""Read only the material graphs required for this appearance revision."""
from pathlib import Path
import json
import unreal as u

P = Path(__file__).resolve().parent
E = u.MaterialEditingLibrary
paths = {
    'overlay': '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',
    'native_gold': '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold',
    'native_instance': '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold',
}
rows = {}
for key, path in paths.items():
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing installed material: ' + path)
    row = {'asset': path, 'nodes': []}
    if isinstance(asset, u.Material):
        for n in E.get_material_expressions(asset):
            item = {'type': n.get_class().get_name(), 'desc': n.get_editor_property('desc')}
            if isinstance(n, u.MaterialExpressionCustom):
                item['code'] = n.get_editor_property('code')
                item['inputs'] = [str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]
            if isinstance(n, (u.MaterialExpressionScalarParameter, u.MaterialExpressionVectorParameter)):
                item['parameter'] = str(n.get_editor_property('parameter_name'))
                v = n.get_editor_property('default_value')
                item['default'] = [v.r, v.g, v.b, v.a] if isinstance(v, u.LinearColor) else v
            row['nodes'].append(item)
    else:
        row['scalar_overrides'] = [{'name': str(v.parameter_info.name), 'value': v.parameter_value}
                                   for v in asset.get_editor_property('scalar_parameter_values')]
        row['vector_overrides'] = [{'name': str(v.parameter_info.name),
            'value': [v.parameter_value.r, v.parameter_value.g, v.parameter_value.b, v.parameter_value.a]}
            for v in asset.get_editor_property('vector_parameter_values')]
    rows[key] = row
(P / 'material_sources.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(rows, ensure_ascii=False))
