"""Read the native packages saved before the report write ran out of disk."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('read_meshy_bed_saved.py')),init_globals={'FURNITURE_REVISION':'ApartmentFastRest20261024R2'})
