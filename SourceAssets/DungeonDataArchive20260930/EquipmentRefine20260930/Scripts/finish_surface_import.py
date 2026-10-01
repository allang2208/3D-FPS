"""Finish this turn's fine-surface UV production on the new V2 equipment only."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'Scripts/import_assets.py'),init_globals={'ALLOW_UNPUBLISHED_REVISION':True},run_name='__main__')
