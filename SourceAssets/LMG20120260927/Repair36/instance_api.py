import unreal as u
M=u.MaterialEditingLibrary;p=u.load_asset('/Game/Weapons/LMG201/Detail35/Materials/M_LMG201_D35_Coat');a=u.load_asset('/Game/Weapons/LMG201/Repair36/Materials/MI_LMG201_R36_Coat')
print('SET_DOC',M.set_material_instance_scalar_parameter_value.__doc__)
print('PARENT',a.get_editor_property('parent'),'NAMES',M.get_scalar_parameter_names(a),'VALUES',a.get_editor_property('scalar_parameter_values'))
result=M.set_material_instance_scalar_parameter_value(a,'Metallic',.3294117647)
print('RESULT',repr(result),'ACTUAL',M.get_material_instance_scalar_parameter_value(a,'Metallic'),'VALUES',a.get_editor_property('scalar_parameter_values'))
