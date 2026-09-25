from pathlib import Path
import unreal

if Path(unreal.Paths.project_dir()).resolve() != Path("D:/FPS3D/FPSGAME").resolve():
    raise RuntimeError("Unexpected editor project")
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
print("WALK_INSPECT_LIVE_COMPILE_BEGIN pie=%s" % (editor.get_game_world() is not None))
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), "LiveCoding.CompileSync")
print("WALK_INSPECT_LIVE_COMPILE_RETURNED")