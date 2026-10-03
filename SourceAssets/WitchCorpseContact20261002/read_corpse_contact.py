"""Read the existing Witch corpse; do not spawn actors or change PIE state."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseContact20261002')
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors = (u.GameplayStatics.get_all_actors_of_class(world, u.WitchRebuiltMonster) if world
          else u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
def vec(value):
    return [value.x, value.y, value.z]
rows = []
for actor in actors:
    if not isinstance(actor, u.WitchRebuiltMonster):
        continue
    mesh = actor.mesh
    knockdown = actor.get_component_by_class(u.HumanoidKnockdownComponent)
    bones = {}
    for name in ('pelvis','spine_02','spine_05','head','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r'):
        position = mesh.get_socket_location(name)
        distance, closest = mesh.get_closest_point_on_collision(position-u.Vector(0,0,1000), name)
        bones[name] = dict(position=vec(position), collision_below=vec(closest),
                           collision_distance=distance, velocity=vec(mesh.get_physics_linear_velocity(name)))
    rows.append(dict(name=actor.get_name(), state=str(actor.get_editor_property('state')),
        phase=str(knockdown.get_editor_property('phase')),
        mesh=mesh.get_editor_property('skeletal_mesh').get_path_name(),
        mesh_world=vec(mesh.get_world_location()), actor_world=vec(actor.get_actor_location()),
        bounds=str(u.SystemLibrary.get_component_bounds(mesh)),
        simulating=mesh.is_simulating_physics(), bones=bones))
result = dict(game_world=bool(world), witches=rows)
(root/'current_contact.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
