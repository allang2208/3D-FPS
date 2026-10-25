"""Update only the revised ordinary-bed entry and mirrored exit routes."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('publish_chair_reuse.py')),
               init_globals={'FURNITURE_REVISION':'MeshyBedSideHands20261024'})
