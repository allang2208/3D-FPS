"""Save the two revised phases on both native bodies and read compressed poses."""
import runpy
from pathlib import Path
for script in ('save_chair_reuse.py','read_meshy_bed_saved.py'):
    runpy.run_path(str(Path(__file__).with_name(script)),init_globals={'FURNITURE_REVISION':'MeshyBedSideHands20261024'})
