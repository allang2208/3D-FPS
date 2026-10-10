"""Read the existing player's camera/body frames; never start play."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonBookPush20261010')
out.mkdir(parents=True, exist_ok=True)
def pack(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
rows = []
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        body = actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body or not body.get_body_mesh():
            continue
        mesh = body.get_body_mesh()
        state = body.get_body_state()
        rows.append(dict(actor=actor.get_name(), body=pack(mesh.get_world_transform()),
            action=str(state.action), variant=str(state.action_variant),
            cameras=[dict(name=c.get_name(), transform=pack(c.get_world_transform()))
                     for c in actor.get_components_by_class(u.CameraComponent)],
            left={n:pack(mesh.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
                  for n in ['clavicle_l','upperarm_l','lowerarm_l','hand_l']}))
(out / 'existing-context.json').write_text(json.dumps(dict(world=str(world), actors=rows), indent=2), encoding='utf-8')
print('BOOK_PUSH_CONTEXT', json.dumps(rows, separators=(',', ':')))
