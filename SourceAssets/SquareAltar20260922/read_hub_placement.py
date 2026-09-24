import json
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world is None:
    raise RuntimeError('Editor has not loaded a world yet; placement has not started.')
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
def vector(v):
    return [v.x, v.y, v.z]
def info(a):
    center, extent = a.get_actor_bounds(False)
    return dict(name=a.get_name(), label=a.get_actor_label(), type=a.get_class().get_name(),
                location=vector(a.get_actor_location()), rotation=str(a.get_actor_rotation()),
                center=vector(center), extent=vector(extent), tags=[str(t) for t in a.tags])
mesh = unreal.load_asset('/Game/Props/SquareAltar20260922/SM_SquareAltar')
nearby = []
if starts:
    origin = starts[0].get_actor_location()
    for a in actors:
        p = a.get_actor_location()
        if (p-origin).length() < 1600 and not isinstance(a, unreal.PlayerStart):
            nearby.append(info(a))
print(json.dumps(dict(world=world.get_path_name(), starts=[info(a) for a in starts],
                     altar=[info(a) for a in actors if 'ColdSteel.ExpeditionAltar' in [str(t) for t in a.tags]],
                     nearby=nearby[:45], mesh_bounds=str(mesh.get_bounding_box()) if mesh else None), ensure_ascii=False))
