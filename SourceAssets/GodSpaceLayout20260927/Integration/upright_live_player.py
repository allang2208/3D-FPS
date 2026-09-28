"""Repair the current user's pawn orientation without restarting or moving it."""
import unreal as u,json
from pathlib import Path
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:raise RuntimeError('No current game world')
pawn=u.GameplayStatics.get_player_character(world,0)
if not pawn:raise RuntimeError('No current player')
before=str(pawn.get_actor_transform())
yaw=pawn.get_control_rotation().yaw
pawn.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),True)
report={'before':before,'applied_rotation':{'pitch':0,'yaw':yaw,'roll':0},'position_changed':False,'restarted':False}
(Path(__file__).parent/'SpawnRepair/live-repair.json').write_text(json.dumps(report,indent=2))
print('LIVE_PLAYER_UPRIGHT '+json.dumps(report))
