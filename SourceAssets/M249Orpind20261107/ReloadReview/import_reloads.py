from pathlib import Path
import subprocess
import unreal as u

if "-run=pythonscript" in u.SystemLibrary.get_command_line().lower():
    query = """Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object { ($_.CommandLine -replace '\\\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*' } |
        Select-Object -ExpandProperty ProcessId"""
    editor = subprocess.check_output(["powershell","-NoProfile","-Command",query],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
    if editor.strip():
        raise RuntimeError("M249_REQUIRE_OPEN_BRIDGE")
targets = {"/Game/Weapons/M249/Animations/A_M249_reload",
           "/Game/Weapons/M249/Animations/A_M249_reload_empty"}
if targets & {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError("The active editor has unsaved edits to an M249 reload")
script = Path(__file__).resolve().parents[1] / "import_motion.py"
exec(compile(script.read_text(encoding="utf8"), str(script), "exec"),
     {"__file__": str(script), "only_roles": ("reload", "reload_empty")})
