"""Save the supported-bed revision on both native bodies and read it back."""
import runpy
from pathlib import Path
for name in ('save_chair_reuse.py','read_meshy_bed_saved.py'):
    runpy.run_path(str(Path(__file__).with_name(name)),init_globals={'FURNITURE_REVISION':'MeshyBedSupportedHands20261024'})
