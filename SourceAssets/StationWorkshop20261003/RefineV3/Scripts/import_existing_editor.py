"""Necessary asset import/save through the current editor's batch mutex."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'Scripts/import_assets.py'),init_globals={'STATION_WORKSHOP_EXISTING_EDITOR_IMPORT':True})
