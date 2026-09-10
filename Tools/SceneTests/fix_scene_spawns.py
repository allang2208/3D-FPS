"""Run after compiling SceneSpawnValidation and closing the interactive editor.
Does not create extra floor meshes or overwrite source asset-pack maps.
"""
import json
from pathlib import Path
import unreal

editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
reports = []
for name in ['DayNight_Lighting', 'L_Normandy_FPS_Test', 'L_MilitaryTrench_FPS_Test']:
    path = '/Game/GameMaps/' + name
    assert editor.load_level(path), path
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = actors_api.get_all_level_actors()
    if name == 'L_MilitaryTrench_FPS_Test':
        assert unreal.SceneSpawnValidation.internalize_test_actors(world), 'Cannot internalize trench test actors'
    starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
    # Sky visuals must not be treated as a walkable ground surface.
    if name == 'DayNight_Lighting':
        floor = next(a for a in actors if a.get_actor_label() == 'Floor')
        center, extent = floor.get_actor_bounds(False)
        top = center.z + extent.z
        component = floor.get_component_by_class(unreal.StaticMeshComponent)
        # Replace the existing zero-thickness visual plane, never add a second floor.
        material = component.get_material(0)
        component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        floor.set_actor_scale3d(unreal.Vector(extent.x / 50, extent.y / 50, 0.4))
        floor.set_actor_location(unreal.Vector(center.x, center.y, top - 20), False, False)
        component.set_collision_profile_name('BlockAll')
        if material:
            component.set_material(0, material)
        for a in actors:
            if a.get_actor_label() == 'BP_FPS_DayNightManager':
                for component in a.get_components_by_class(unreal.StaticMeshComponent):
                    if component.get_name() == 'SM_SkySphere':
                        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if starts:
        near = starts[0].get_actor_location()
        rotation = starts[0].get_actor_rotation()
    else:
        assert name == 'DayNight_Lighting', 'Missing source start: ' + name
        floor = next(a for a in actors if a.get_actor_label() == 'Floor')
        center, extent = floor.get_actor_bounds(False)
        near = unreal.Vector(center.x, center.y, center.z + extent.z + 110)
        rotation = unreal.Rotator(0, 0, 0)
    safe = unreal.SceneSpawnValidation.find_safe_spawn(world, near)
    assert safe is not None, 'No safe ground; refusing to save ' + name
    start = starts[0] if starts else actors_api.spawn_actor_from_class(unreal.PlayerStart, safe, rotation)
    start.set_actor_location(safe, False, False)
    start.set_actor_label('PlayerStart_SceneTest')
    start.set_editor_property('is_spatially_loaded', False)
    assert editor.save_current_level(), 'Save failed: ' + name
    assert editor.load_level(path), 'Reload failed: ' + name
    loaded = [a for a in actors_api.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    assert len(loaded) == 1, 'Expected exactly one start in ' + name
    assert not loaded[0].get_editor_property('is_spatially_loaded')
    reports.append({'map': path, 'start': str(loaded[0].get_actor_location()), 'always_loaded': True})
    (Path(unreal.Paths.project_saved_dir())/'SceneTests/spawn-fix.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
unreal.log('SCENE_SPAWN_FIX_OK ' + json.dumps(reports))
