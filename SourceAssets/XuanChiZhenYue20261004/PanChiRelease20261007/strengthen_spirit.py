"""Rebuild only the installed dragon body material; preserve other release layers."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().with_name('install_assets.py')),
              init_globals={'PANCHI_SPIRIT_ONLY':True})
