from pathlib import Path
import runpy
P=Path(__file__).parent
runpy.run_path(str(P/'import_assets.py'),run_name='__main__')
runpy.run_path(str(P/'import_hud.py'),run_name='__main__')
