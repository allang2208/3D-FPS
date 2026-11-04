import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
L=u.MaterialEditingLibrary
result=json.loads((ROOT/'material-state.json').read_text(encoding='utf-8'))
def read_mat(path):
    obj = u.load_asset(path)
    if not obj: result['missing'].append(path); return
    if isinstance(obj,u.MaterialInstanceConstant):
        parent = obj.get_editor_property('parent')
        if parent: read_mat(parent.get_path_name())
        if True: result['bindings'][obj.get_path_name()] = [parent.get_path_name()]
        return
    if not isinstance(obj,u.Material) or obj.get_path_name() in result['materials']: return
    row = {'nodes': [], 'outputs': {}}
    for name in ['MP_FRONT_MATERIAL','MP_EMISSIVE_COLOR','MP_OPACITY']:
        n = L.get_material_property_input_node(obj,getattr(u.MaterialProperty,name))
        row['outputs'][name] = n.get_name() if n else None
    for n in L.get_material_expressions(obj):
        info = {'name':n.get_name(),'class':n.get_class().get_name(),
                'input_names':list(L.get_material_expression_input_names(n)),
                'input_nodes':[x.get_name() if x else None for x in L.get_inputs_for_material_expression(obj,n)]}
        if isinstance(n,u.MaterialExpressionCustom): info['code'] = n.get_editor_property('code')
        if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
            v=n.get_editor_property('default_value')
            info.update(parameter=str(n.get_editor_property('parameter_name')),value=[v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v)
        row['nodes'].append(info)
    result['materials'][obj.get_path_name()] = row


for path in json.loads((ROOT/'knife-paths.json').read_text()):read_mat(path)
(ROOT/'material-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNE_WITH_KNIFE_MATERIALS',len(result['materials']))
