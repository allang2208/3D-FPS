import unreal
assets=[unreal.load_asset('/Game/Monsters/PoisonMaggot/Materials/'+n) for n in ['M_PoisonMaggot_Skin','M_PoisonMaggot_Venom','M_AuditGround']]
assert unreal.PoisonMaggotMonster.compile_material_assets(assets),'Material has no compiled texture bindings'
for asset in assets:unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
unreal.log('MAGGOT_MATERIAL_COMPILE_COMPLETE')
