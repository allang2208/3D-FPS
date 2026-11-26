"""Write the nape revision to its own four mesh packages and icon package."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('helmet_contour_save.py')),
               init_globals={'HELMET_REVISION': 'HelmetNapeR3'})
