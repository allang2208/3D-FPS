"""Read the saved pus material graph for a reported visibility failure; no gameplay."""
import json
from pathlib import Path
import unreal as u

lib = u.MaterialEditingLibrary
mat = u.load_asset('/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus')
instance = u.load_asset('/Game/Monsters/FatZombieMeshy/Pus/MI_FatZombie_Pus')
report = {'properties': {}, 'outputs': {}, 'expressions': [], 'instance_scalars': {}}
for key in ('material_domain', 'blend_mode', 'shading_model', 'two_sided', 'use_material_attributes',
            'translucency_lighting_mode', 'translucency_pass', 'disable_depth_test', 'is_sky'):
    report['properties'][key] = str(mat.get_editor_property(key))
for key in ('BASE_COLOR', 'NORMAL', 'OPACITY', 'OPACITY_MASK', 'WORLD_POSITION_OFFSET'):
    expr = lib.get_material_property_input_node(mat, getattr(u.MaterialProperty, 'MP_'+key))
    report['outputs'][key] = expr.get_name() if expr else None
for expr in lib.get_material_expressions(mat):
    row = {'name': expr.get_name(), 'class': expr.get_class().get_name()}
    if isinstance(expr, u.MaterialExpressionDepthFade):
        row['fade_distance_default'] = expr.get_editor_property('fade_distance_default')
    if isinstance(expr, u.MaterialExpressionCustom):
        row['code'] = expr.get_editor_property('code')
        row['inputs'] = [x.get_name() if x else None for x in lib.get_inputs_for_material_expression(mat, expr)]
    report['expressions'].append(row)
for name in lib.get_scalar_parameter_names(instance):
    report['instance_scalars'][str(name)] = lib.get_material_instance_scalar_parameter_value(instance, name)
out = Path('D:/FPS3D/FPSGAME/Saved/FatZombiePus/visibility_before.json')
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('FAT_PUS_VISIBILITY_RECORDED')
