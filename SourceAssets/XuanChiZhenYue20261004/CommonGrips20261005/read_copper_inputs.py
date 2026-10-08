"""Read the newly authored copper graph inputs to finish its pending connection."""
import unreal as u,json
E=u.MaterialEditingLibrary
m=u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/CommonGrips20261005/Materials/M_XuanChi_GripCopper')
slab=E.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
base=E.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
def desc(n):
    return {'name':n.get_name(),'class':n.get_class().get_name(),
        'pins':[str(p) for p in E.get_material_expression_input_names(n)],
        'sources':[x.get_name() if x else None for x in E.get_inputs_for_material_expression(m,n)]} if n else None
print(json.dumps({'base':desc(base),'base_pin':str(E.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)),
    'slab':desc(slab),'desaturations':[desc(n) for n in E.get_material_expressions(m) if isinstance(n,u.MaterialExpressionDesaturation)]}))
