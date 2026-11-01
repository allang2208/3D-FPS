"""Save the revised hand clips and registry; preserve all fitted geometry."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().with_name('install.py')),init_globals={'ANIMATIONS_ONLY':True})
