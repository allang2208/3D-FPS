import runpy
from pathlib import Path
P=Path(__file__).parent
runpy.run_path(str(P/'import_assets.py'),run_name='__main__')
runpy.run_path(str(P/'readback_ue.py'),run_name='__main__')
