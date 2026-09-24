"""Run the owned imports and catalog save in one background commandlet."""
import runpy
from pathlib import Path

scripts=Path(__file__).resolve().parent
runpy.run_path(str(scripts/'import_assets.py'),run_name='__main__')
runpy.run_path(str(scripts/'install.py'),run_name='__main__')
