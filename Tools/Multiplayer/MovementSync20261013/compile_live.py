"""Apply function-only networking repairs to the existing editor; never start PIE."""
from pathlib import Path
import unreal

output = Path(unreal.Paths.project_saved_dir()) / "MultiplayerMovementFix20261013"
output.mkdir(parents=True, exist_ok=True)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError("Stop the current play session before changing the profile wire format.")
log = Path(unreal.Paths.project_log_dir()) / "FPSGAME.log"
offset = log.stat().st_size if log.exists() else 0
unreal.log("MOVEMENT_SYNC_FIX_COMPILE_BEGIN")
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), "LiveCoding.CompileSync")
unreal.log("MOVEMENT_SYNC_FIX_COMPILE_RETURN")
if log.exists():
    with log.open("rb") as stream:
        stream.seek(offset)
        (output / "live-compile.log").write_text(stream.read().decode("utf-8", errors="replace"), encoding="utf-8")
print("MOVEMENT_SYNC_FIX_COMPILE_RETURNED")
