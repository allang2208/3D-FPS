import unreal
lib=unreal.EditorAssetLibrary
mesh=unreal.load_asset('/Game/Monsters/PoisonMaggot/SK_PoisonMaggot')
pa=unreal.PoisonMaggotMonster.create_physics_asset(mesh)
assert pa
for asset in [pa,mesh,mesh.skeleton]:lib.save_loaded_asset(asset,False)
unreal.log('MAGGOT_PHYSICS_UPDATED')
