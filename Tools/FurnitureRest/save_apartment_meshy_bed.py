"""Save the fitted apartment entry, rest and exit on both native skeletons."""
import runpy
from pathlib import Path
for script in ('save_chair_reuse.py','read_meshy_bed_saved.py','read_kaitlin_bed_arms.py'):
    runpy.run_path(str(Path(__file__).with_name(script)),init_globals={'FURNITURE_REVISION':'MeshyApartmentBed20261024'})
