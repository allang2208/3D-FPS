"""Import only the sprint-attack clip (SprintAttack, two-handed jump chop) through import_kukri.py.

Mesh, textures and material are revision-gated in import_kukri.py and left as they are.  Runs as a commandlet
(-run=pythonscript -script=<this file>) or inside a live editor via Tools/AssetPipeline/mcp_call_codex.ps1
-PythonScript.  Never runs PIE or tests."""
from pathlib import Path

KUKRI_CLIPS = ('SprintAttack',)
_src = Path(r"D:\FPS3D\FPSGAME\SourceAssets\Kukri20261020\import_kukri.py")
exec(compile(_src.read_text('utf-8'), str(_src), 'exec'))
