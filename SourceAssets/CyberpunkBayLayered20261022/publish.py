from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parent
runpy.run_path(str(ROOT/'import_assets.py'),run_name='__main__')
runpy.run_path(str(ROOT/'install_level.py'),run_name='__main__')
