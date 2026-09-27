"""Background production batch: import/save meshes, then publish the catalog."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
runpy.run_path(str(ROOT/'import_assets.py'),run_name='__main__')
runpy.run_path(str(ROOT/'install.py'),run_name='__main__')
