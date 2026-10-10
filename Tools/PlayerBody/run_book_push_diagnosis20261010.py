"""Invoke only the requested transient animation-proxy comparison."""
from pathlib import Path
import unreal as u

out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonBookPush20261010/proxy-diagnosis-final.json')
before=out.stat().st_mtime_ns if out.exists() else None
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'fps.body.DiagnoseBookPush '+out.as_posix())
if not out.exists() or out.stat().st_mtime_ns == before:
    raise RuntimeError('Book push diagnosis did not produce a fresh report')
print('BOOK_PUSH_DIAGNOSIS_COMPLETE',out.as_posix())
