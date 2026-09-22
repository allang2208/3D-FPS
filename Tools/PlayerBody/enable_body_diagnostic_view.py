"""Use the existing session-only F6 option for the user-requested body diagnosis."""
from pathlib import Path
import unreal as u

if Path(u.Paths.project_dir()).resolve() != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected project")
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world is None:
    raise RuntimeError("PIE required")
instance = u.GameplayStatics.get_game_instance(world)
player = u.GameplayStatics.get_player_controller(world, 0)
for obj in u.ObjectIterator(u.DevelopmentTuningSubsystem):
    if obj.get_outer() == instance:
        if not obj.set_enabled(u.DevelopmentTuningOption.THIRD_PERSON_VIEW, True, player):
            raise RuntimeError("Development view switch rejected")
        print("Enabled third-person through the existing session-only developer option.")
        break
else:
    raise RuntimeError("No development subsystem found for the active play world")
