import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('repair_glow_material.py')),init_globals={'PANCHI_LIVE_CAPTURE_ONLY':True})
