import json,runpy
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/BarePalmHoleRepair20261014')
runpy.run_path(str(r/'read_current.py'),init_globals={'MESH_PATHS':json.loads((r/'scope.json').read_text())})
