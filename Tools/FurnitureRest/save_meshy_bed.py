"""Save the ordinary-bed candidate and its native female counterpart."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('save_chair_reuse.py')),
               init_globals={'FURNITURE_REVISION':'MeshyBed20261024'})
runpy.run_path(str(Path(__file__).with_name('read_meshy_bed_saved.py')))
