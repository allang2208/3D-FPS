"""Read-only snapshot of the running pawn and Dragon Breath launch geometry."""
import json
from pathlib import Path
import unreal as u


def prop(obj, name):
    try:
        value = obj.get_editor_property(name)
        return value.get_path_name() if isinstance(value, u.Object) else str(value)
    except Exception as exc:
        return 'unavailable: ' + str(exc)[:120]


world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result = {'world': world.get_path_name() if world else None, 'pawns': []}
if world:
    for pawn in u.GameplayStatics.get_all_actors_of_class(world, u.Pawn):
        if not pawn.is_player_controlled():
            continue
        row = {'pawn': pawn.get_path_name(), 'location': str(pawn.get_actor_location()),
               'eye_height': prop(pawn, 'base_eye_height'), 'components': []}
        controller = pawn.get_controller()
        row['control_rotation'] = str(controller.get_control_rotation())
        if isinstance(controller, u.PlayerController):
            row['view'] = str(controller.get_player_view_point())
        for component in pawn.get_components_by_class(u.ActorComponent):
            kind = component.get_class().get_name()
            name = component.get_name()
            if kind == 'FPSFireMagicComponent':
                row['components'].append({'kind': kind, 'system': prop(component, 'dragon_system'),
                                          'state': prop(component, 'dragon_state')})
            elif kind == 'FPSFireballComponent':
                row['components'].append({'kind': kind, 'phase': str(component.get_hand_phase())})
            elif kind == 'FPSCombatHealthComponent':
                row['components'].append({'kind': kind, 'health': prop(component, 'health')})
            elif name == 'StaffAssembly' or isinstance(component, u.CameraComponent):
                row['components'].append({'name': name, 'transform': str(component.get_world_transform())})
        result['pawns'].append(row)
out = Path('D:/FPS3D/FPSGAME/Saved/DragonReadiness20261014/runtime-snapshot.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
