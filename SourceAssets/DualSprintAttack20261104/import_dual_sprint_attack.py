"""Import only A_Kukri_DualSprintAttack (the pair's sprint attack, author_dual_sprint_attack.py) through
Kukri20261020/import_kukri.py; nothing else is re-saved.  Reads this folder's Clips/DualSprintAttack.json, writes
import_receipt.json here.  Runs as a commandlet (UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
-unattended -nosplash) or inside a live editor via Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript.
Never runs PIE or tests."""
from pathlib import Path

_here = Path(r"D:\FPS3D\FPSGAME\SourceAssets\DualSprintAttack20261104\import_dual_sprint_attack.py")
_src = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py")
exec(compile(_src.read_text('utf-8'), str(_src), 'exec'),
     {'__file__': str(_here), '__name__': '__main__', 'KUKRI_CLIPS': ('DualSprintAttack',)})
