"""Import the dual-kukri locomotion clips (A_Kukri_DualIdle / DualWalk / DualRun) through Kukri20261020/import_kukri.py.

The clips are read from this folder's Clips/ and the receipt is written here (import_receipt.json); mesh, textures and
material are revision-gated in import_kukri.py and left as they are.  Runs as a commandlet
(UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file> -unattended -nosplash -nop4) or inside
a live editor via Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript.  Never runs PIE or tests."""
from pathlib import Path

_here = Path(r"D:\FPS3D\FPSGAME\SourceAssets\DualKukriIdle20261025\import_dual_kukri.py")
_src = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py")
exec(compile(_src.read_text('utf-8'), str(_src), 'exec'),
     {'__file__': str(_here), '__name__': '__main__', 'KUKRI_CLIPS': ('DualIdle', 'DualWalk', 'DualRun')})
