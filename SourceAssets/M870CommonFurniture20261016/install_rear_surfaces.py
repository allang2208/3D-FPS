import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('install.py')),init_globals={'ONLY_PARTS':('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip')})
