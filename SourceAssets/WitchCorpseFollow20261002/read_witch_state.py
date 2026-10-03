import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseFollow20261002')
out.mkdir(parents=True, exist_ok=True)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors = (u.GameplayStatics.get_all_actors_of_class(world, u.WitchRebuiltMonster) if world
          else u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
rows = []
for actor in actors:
    if not isinstance(actor, u.WitchRebuiltMonster):
        continue
    mesh = actor.mesh
    knockdown = actor.get_component_by_class(u.HumanoidKnockdownComponent)
    def vec(value):
        return [value.x, value.y, value.z]
    row = dict(name=actor.get_name(), state=str(actor.get_editor_property('state')),
               phase=str(knockdown.get_editor_property('phase')),
               mesh_asset=mesh.get_editor_property('skeletal_mesh').get_path_name(),
               mesh_world=vec(mesh.get_world_location()),
               anim_class=mesh.get_anim_instance().get_class().get_path_name() if mesh.get_anim_instance() else None,
               cloth_weight=mesh.get_editor_property('cloth_blend_weight'),
               cloth_suspended=mesh.is_clothing_simulation_suspended(),
               bones={name: dict(position=vec(mesh.get_socket_location(name)),
                                 velocity=vec(mesh.get_physics_linear_velocity(name)))
                      for name in ('pelvis', 'calf_l', 'calf_r', 'foot_l', 'foot_r')},
               components=[dict(name=c.get_name(), cls=c.get_class().get_path_name())
                           for c in actor.get_components_by_class(u.MeshComponent)])
    rows.append(row)
result = dict(game_world=bool(world), witches=rows)
(out/'current_witch_state.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
