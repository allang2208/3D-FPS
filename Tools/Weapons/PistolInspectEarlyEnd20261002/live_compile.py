"""Compile the inspect input fix in the already-running FPSGAME editor."""
from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected editor project")
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = editor.get_game_world() or editor.get_editor_world()
print("PISTOL_INSPECT_INPUT_FIX_COMPILE_BEGIN")
unreal.SystemLibrary.execute_console_command(world, "LiveCoding.CompileSync")
print("PISTOL_INSPECT_INPUT_FIX_COMPILE_RETURNED; compiler log determines completion")
