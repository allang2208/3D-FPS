import unreal as u
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
path='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR7/Materials/MI_ChimneyFlueSoot'
source='/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A'
mat=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source,path)
if not mat:raise RuntimeError('Chimney soot material')
mat.modify()
for name,color in [('TS00_BaseColor_Tint',(.055,.047,.039)),('TS01_BaseColor_Tint',(.09,.075,.06)),('TS02_BaseColor_Tint',(.17,.145,.12)),('TS03_BaseColor_Tint',(.055,.058,.05))]:
    L.set_material_instance_vector_parameter_value(mat,name,u.LinearColor(*color,1))
L.update_material_instance(mat)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Save chimney soot')
