"""An isolated, obstacle-free floor for the existing movement/reload input audit."""
import unreal

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
path = '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation'
assert not unreal.EditorAssetLibrary.does_asset_exist(path), path
assert level.new_level(path)
floor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -50))
floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
floor.set_actor_scale3d(unreal.Vector(200, 200, 1))
floor.set_actor_label('RigAudit_ClearFloor')
actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 100))
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(-45, -35, 0))
sun.light_component.set_editor_property('intensity', 4.0)
sun.light_component.set_editor_property('forward_shading_priority', 1)
fill = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(-25, 140, 0))
fill.light_component.set_editor_property('intensity', 2.0)
fill.light_component.set_editor_property('forward_shading_priority', 0)
fill.light_component.set_editor_property('atmosphere_sun_light', False)
actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 400))
actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0))
assert level.save_current_level()
unreal.log('M4_RIG_VALIDATION_MAP_PASS')
