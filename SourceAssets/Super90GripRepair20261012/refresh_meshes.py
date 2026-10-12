"""Refresh repaired interface UVs after the scoped profile publication."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('import_assets.py')),init_globals={'MESH_ONLY':True})
runpy.run_path(str(Path(__file__).with_name('readback_saved.py')))
