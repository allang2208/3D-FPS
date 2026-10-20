import json,runpy
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/BarePalmHoleRepair20261014')
paths=[v['path'] for v in json.loads((r/'triangulated_plan.json').read_text())]
runpy.run_path(str(r/'read_current.py'),init_globals={'MESH_PATHS':paths,'SNAPSHOT_SUBDIR':'Final'})
