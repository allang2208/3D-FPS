import runpy
from pathlib import Path
R=Path(__file__).resolve().parent
runpy.run_path(str(R/'build_assets.py'),run_name='__main__')
runpy.run_path(str(R/'install_level.py'),run_name='__main__')
