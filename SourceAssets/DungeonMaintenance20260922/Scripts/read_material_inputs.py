import unreal as u
m=u.load_asset('/Game/Dungeons/AtmosphereV2/Maintenance/Materials/M_Maintenance_Enamel')
for cls in (u.MaterialExpressionSaturate,u.MaterialExpressionComponentMask):
 n=u.MaterialEditingLibrary.create_material_expression(m,cls)
 print(cls.__name__,u.MaterialEditingLibrary.get_material_expression_input_names(n))
 u.MaterialEditingLibrary.delete_material_expression(m,n)
