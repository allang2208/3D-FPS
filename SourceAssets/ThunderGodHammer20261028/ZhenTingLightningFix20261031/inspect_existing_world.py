"""Read the current scene only; do not start PIE or execute an attack."""
import unreal as u, json
from pathlib import Path

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_game_world()
result = {'game_world': world.get_path_name() if world else None}
if world:
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    result['pawn'] = pawn.get_path_name() if pawn else None
    if pawn:
        result['location'] = str(pawn.get_actor_location())
        result['view'] = str(pawn.get_control_rotation())
        result['trace_api'] = u.SystemLibrary.line_trace_single.__doc__
        result['hit_api'] = u.HitResult.__doc__
Path(__file__).with_name('existing_world.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
