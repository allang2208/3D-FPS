"""The shared route rebuild chain calls the scoped treatment rules."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
helpers=runpy.run_path(str(ROOT/'Scripts/catalog_rules.py'))
extend=helpers['extend']
asset_paths=helpers['paths']
