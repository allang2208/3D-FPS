"""Install the ordinary-bed clips, timing and matching foot-end approach."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_chair_reuse.py')),
               init_globals={'FURNITURE_REVISION':'MeshyBed20261024'})
