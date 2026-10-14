"""Apply function-only reload tempo changes without starting or stopping PIE."""
from pathlib import Path
from datetime import datetime, timezone
import json
import unreal

project = Path("D:/FPS3D/FPSGAME")
if Path(unreal.Paths.project_dir()).resolve() != project.resolve():
    raise RuntimeError("Unexpected editor project")
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
receipt_path = project / "Saved/DualReloadPower20261013/live_compile.json"
receipt_path.parent.mkdir(parents=True, exist_ok=True)
receipt = {"started_utc": datetime.now(timezone.utc).isoformat(),
           "command": "LiveCoding.CompileSync", "runtime_tested": False}
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
world = editor.get_game_world() or editor.get_editor_world()
unreal.SystemLibrary.execute_console_command(world, "LiveCoding.CompileSync")
receipt["returned_utc"] = datetime.now(timezone.utc).isoformat()
receipt["status"] = "Command returned; compiler log determines success"
receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("DUAL_RELOAD_POWER_COMPILE_RETURNED; inspect compiler result")
