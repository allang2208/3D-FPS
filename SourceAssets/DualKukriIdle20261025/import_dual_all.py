"""Import every dual kukri clip (hold, walk, run, combo 1-3, heavy charge / release, draw) through Kukri20261020/import_kukri.py
-- after a change of the dual hold (DualIdle frame 0), which every dual clip starts and ends on.  Reads this folder's
Clips/, writes import_receipt.json here.  Runs inside a live editor via Tools/AssetPipeline/mcp_call_codex.ps1
-PythonScript, or as a commandlet when no editor holds the packages.  Never runs PIE or tests."""
from pathlib import Path

_here = Path(r"D:\FPS3D\FPSGAME\SourceAssets\DualKukriIdle20261025\import_dual_kukri.py")
_src = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py")
exec(compile(_src.read_text('utf-8'), str(_src), 'exec'),
     {'__file__': str(_here), '__name__': '__main__',
      'KUKRI_CLIPS': ('DualIdle', 'DualWalk', 'DualRun', 'DualAttack', 'DualAttack2', 'DualAttack3', 'DualHeavyCharge',
                      'DualHeavyRelease', 'DualEquip')})
