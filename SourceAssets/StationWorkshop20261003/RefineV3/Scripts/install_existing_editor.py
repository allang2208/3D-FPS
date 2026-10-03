"""Necessary production/preview map save; never starts PIE or opens another editor."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'Scripts/install_scenes.py'),init_globals={'STATION_WORKSHOP_EXISTING_EDITOR_INSTALL':True})
