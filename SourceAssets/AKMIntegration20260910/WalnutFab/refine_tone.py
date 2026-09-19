import unreal as u
P='/Game/Weapons/AKMIntegration/WalnutFab';lib=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
mi=u.load_asset(P+'/MI_AKM_RedBrownWalnut') if u.EditorAssetLibrary.does_asset_exist(P+'/MI_AKM_RedBrownWalnut') else assets.create_asset('MI_AKM_RedBrownWalnut',P,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(mi,u.load_asset(P+'/M_AKM_SatinWalnut'));lib.update_material_instance(mi)
lib.set_material_instance_vector_parameter_value(mi,'RedBrownTint',u.LinearColor(.8,.38,.25,1));lib.update_material_instance(mi)
v=lib.get_material_instance_vector_parameter_value(mi,'RedBrownTint');assert abs(v.r-.8)<.001
assert u.EditorAssetLibrary.save_loaded_asset(mi,False)
mesh=u.load_asset(P+'/SK_AKM_MannyNative');slots=mesh.get_editor_property('materials')
for i,s in enumerate(slots):
 if str(s.material_slot_name)=='M_AKMR_Walnut':s.material_interface=mi;slots[i]=s
mesh.set_editor_property('materials',slots);assert u.EditorAssetLibrary.save_loaded_asset(mesh,False)
u.log('AKM_WALNUT_TONE_PASS')
