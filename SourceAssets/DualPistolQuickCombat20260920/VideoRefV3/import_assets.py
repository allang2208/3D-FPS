"""Import both strike-hand variants, preserving the V2 runtime asset packages."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parents[1] / 'import_assets.py'), init_globals={
    'MOTION_REVISION': 'VideoRefV3', 'DESTINATION_REVISION': 'VideoRefV3'
})
