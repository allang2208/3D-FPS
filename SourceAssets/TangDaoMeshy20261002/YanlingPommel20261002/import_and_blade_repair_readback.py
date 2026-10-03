"""Finish new asset creation and separately read back the requested blade repair."""
import runpy
from pathlib import Path
P=Path(__file__).resolve().parent
runpy.run_path(str(P/'import_assets.py'),run_name='__main__')
runpy.run_path(str(P.parent/'TengyunBlade20261002/Repair20261002/diagnose_blade.py'),run_name='__main__')
