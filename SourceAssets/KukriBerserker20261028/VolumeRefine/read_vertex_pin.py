import unreal as u
L=u.MaterialEditingLibrary
m=u.load_asset('/Game/Weapons/Kukri20261020/Berserker20261028/Materials/M_Berserker_Factory')
for n in L.get_material_expressions(m):
    if isinstance(n,(u.MaterialExpressionVertexInterpolator,u.MaterialExpressionPreSkinnedPosition)):
        print(n.get_class().get_name(),'inputs',list(L.get_material_expression_input_names(n)),'outputs',list(L.get_material_expression_output_names(n)))
