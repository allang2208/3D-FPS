import unreal,json
from pathlib import Path
mesh=unreal.load_asset('/Game/Monsters/HandBrain/SK_HandBrain')
a=unreal.HandBrainMonster.create_physics_asset(mesh)
assert a
unreal.EditorAssetLibrary.save_loaded_asset(a)
unreal.EditorAssetLibrary.save_loaded_asset(mesh)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
t=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector());t.skeletal_mesh_component.set_skeletal_mesh_asset(mesh)
origin,extent=t.get_actor_bounds(False)
assert extent.x<200 and extent.y<200 and extent.z<250,str(extent)
Path('D:/FPS3D/FPSGAME/Saved/HandBrain/physics-fixed.json').write_text(json.dumps({'extent_cm':[extent.x,extent.y,extent.z],'physics':a.get_path_name()}))
actors.destroy_actor(t)
unreal.log('HANDBRAIN_PHYSICS_REBUILT')
