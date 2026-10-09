"""Read the user's latest traversal rejection, without moving actors or running PIE."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=ed.get_game_world()
result=dict(pie=bool(world),world=world.get_path_name() if world else None)
if world:
    c=u.GameplayStatics.get_player_character(world,0)
    if c:
        t=c.get_component_by_class(u.FPSTraversalComponent)
        result.update(location=str(c.get_actor_location()),view=str(c.get_control_rotation()))
        if t:
            for key,target in [('last',t.get_editor_property('last_jump_target')),('current',t.find_target(True,True))]:
                result[key]=dict(reason=str(target.reason),action=str(target.action),probe=str(target.probe),
                    obstacle=target.obstacle.get_owner().get_name() if target.obstacle else None,
                    obstacle_mesh=str(target.obstacle.get_editor_property('static_mesh').get_path_name()) if isinstance(target.obstacle,u.StaticMeshComponent) and target.obstacle.static_mesh else None)
(ROOT/'Receipts/live-window-v6.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
