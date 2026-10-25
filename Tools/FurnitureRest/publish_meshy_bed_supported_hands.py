"""Apply only the ordinary-bed enter/exit clips and matching eye tracks."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_chair_reuse.py')),init_globals={'FURNITURE_REVISION':'MeshyBedSupportedHands20261024'})
