"""Necessary compilation of the new catalog-driven room selection."""
import unreal as u
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active play; room pool compile pending')
log=ROOT.parents[1]/'Saved/Logs/FPSGAME.log'
offset=log.stat().st_size if log.exists() else 0
u.SystemLibrary.execute_console_command(editor.get_editor_world(),'LiveCoding.CompileSync')
if log.exists():
    with log.open('rb') as stream:
        stream.seek(offset)
        (ROOT/'Receipts/live-compile.log').write_bytes(stream.read())
print('ROOM_POOL_LIVE_COMPILE_RETURNED')
