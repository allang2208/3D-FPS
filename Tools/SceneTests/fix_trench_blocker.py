"""Apply in full editor Python, with the interactive project closed."""
import json
from pathlib import Path
import unreal

path = '/Game/GameMaps/L_MilitaryTrench_FPS_Test'
editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert editor.load_level(path)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actors_api.get_all_level_actors()
cube = next(a for a in actors if a.get_name() == 'StaticMeshActor_UAID_0017B600C5684FAA02_1776864923')
component = cube.get_component_by_class(unreal.StaticMeshComponent)
assert component.static_mesh.get_path_name() == '/Engine/BasicShapes/Cube.Cube'
report = {'actor': cube.get_path_name(), 'materials': [str(component.get_material(i)) for i in range(component.get_num_materials())],
          'visible': component.is_visible(), 'previous_pawn_response': str(component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN))}
# Preserve geometry, material, rendering effects and non-Pawn collision behavior.
cube.modify()
component.modify()
component.set_collision_profile_name('Custom')
component.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_IGNORE)
start = next(a for a in actors if isinstance(a, unreal.PlayerStart))
safe = unreal.SceneSpawnValidation.find_safe_spawn(world, start.get_actor_location())
assert safe is not None, 'No safe ground after removing blocker; no save'
start.set_actor_location(safe, False, False)
assert editor.save_current_level()
assert editor.load_level(path)
cube = next(a for a in actors_api.get_all_level_actors() if a.get_name() == 'StaticMeshActor_UAID_0017B600C5684FAA02_1776864923')
assert cube.get_component_by_class(unreal.StaticMeshComponent).get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN) == unreal.CollisionResponseType.ECR_IGNORE
report['new_start'] = str(safe)
(Path(unreal.Paths.project_saved_dir())/'SceneTests/trench-blocker-fix.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('TRENCH_BLOCKER_FIX_SAVED ' + json.dumps(report))
