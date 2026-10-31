"""Read the current bed placements needed to reuse the approved bedroom asset."""
from pathlib import Path
import json
import unreal as u

R = Path(__file__).resolve().parent
MAP = '/Game/GameMaps/L_CyberpunkApartment'
s = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = s.get_editor_world()
game = s.get_game_world()
dirty = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
result = dict(editor_world=world.get_path_name() if world else None,
              game_world=game.get_path_name() if game else None,
              dirty_maps=dirty, beds=[])
if not game and not dirty:
    if not world or world.get_path_name().split('.')[0] != MAP:
        world = u.EditorLoadingAndSavingUtils.load_map(MAP)
    for a in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
        c = a.static_mesh_component
        if not c.static_mesh:
            continue
        label = a.get_actor_label()
        path = c.static_mesh.get_path_name()
        if label not in ('AP_Master_Bed', 'AP_Bed2_Bed', 'AP_Bed3_Bed', 'BP_FootThrow'):
            if not any(word in path for word in ('BedKing.', 'BedQueen.', 'AP14_Bed.', 'BP3_BedRefined.')):
                continue
        rot = a.get_actor_rotation()
        bounds = c.static_mesh.get_bounding_box()
        result['beds'].append(dict(actor=label, mesh=path,
            position=list(a.get_actor_location().to_tuple()),
            rotation=dict(pitch=rot.pitch, yaw=rot.yaw, roll=rot.roll),
            scale=list(a.get_actor_scale3d().to_tuple()),
            bounds_min=list(bounds.min.to_tuple()), bounds_max=list(bounds.max.to_tuple()),
            materials=[m.get_path_name() if m else None for m in c.get_materials()],
            tags=[str(t) for t in a.tags],
            parent=a.get_attach_parent_actor().get_actor_label() if a.get_attach_parent_actor() else None,
            mobility=str(c.get_editor_property('mobility')),
            collision_profile=str(c.get_collision_profile_name()),
            collision_enabled=str(c.get_collision_enabled())))
(R/'source.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result))
