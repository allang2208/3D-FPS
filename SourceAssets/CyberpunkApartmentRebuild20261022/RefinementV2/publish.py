"""Single-process, scoped import and publication entry; never starts PIE."""
from pathlib import Path
import runpy
root=Path(__file__).resolve().parent
runpy.run_path(str(root/'import_assets.py'),run_name='__main__')
runpy.run_path(str(root/'install_level.py'),run_name='__main__')
