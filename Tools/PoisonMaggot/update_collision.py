import unreal
lib=unreal.EditorAssetLibrary;bp=unreal.load_asset('/Game/Monsters/PoisonMaggot/BP_PoisonMaggot')
unreal.BlueprintEditorLibrary.compile_blueprint(bp);cdo=unreal.get_default_object(bp.generated_class())
cdo.capsule_component.set_capsule_size(70,70,False);cdo.mesh.set_relative_location(unreal.Vector(0,0,-70),False,False)
lib.save_loaded_asset(bp,False)
assert cdo.capsule_component.get_unscaled_capsule_radius()==70
unreal.log('MAGGOT_COLLISION_UPDATED')
