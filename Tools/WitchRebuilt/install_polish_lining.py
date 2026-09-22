import unreal as u
L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
path='/Game/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Lining'
m=u.load_asset(path) if L.does_asset_exist(path) else AT.create_asset('M_WitchRebuilt_Lining','/Game/Monsters/WitchRebuilt/Materials',u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(m);m.set_editor_property('two_sided',True);m.set_editor_property('used_with_skeletal_mesh',True)
slab=M.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
for prop,pin,value in [(u.MaterialProperty.MP_BASE_COLOR,'BaseColor',(.035,.026,.016)),(u.MaterialProperty.MP_ROUGHNESS,'Roughness',.88),(u.MaterialProperty.MP_SPECULAR,'Specular',.28)]:
    n=M.create_material_expression(m,u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
    n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value)
    M.connect_material_property(n,'',prop);M.connect_material_expressions(n,'',slab,pin)
M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);M.recompile_material(m)
if not L.save_loaded_asset(m,False):raise RuntimeError('Lining save failed')
print('Saved fitted inner fabric material')
