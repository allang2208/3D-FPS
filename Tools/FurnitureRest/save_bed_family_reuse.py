import runpy
from pathlib import Path
HERE=Path(__file__).parent;REVISION=globals().get('FURNITURE_REVISION','BedFamilyReuse20261024')
runpy.run_path(str(HERE/'save_chair_reuse.py'),init_globals={'FURNITURE_REVISION':REVISION,'NATIVE_REVERSE_EXITS':True})
runpy.run_path(str(HERE/'read_meshy_bed_saved.py'),init_globals={'FURNITURE_REVISION':REVISION})
print('BED_FAMILY_NATIVE_SAVE_COMPLETE',flush=True)
