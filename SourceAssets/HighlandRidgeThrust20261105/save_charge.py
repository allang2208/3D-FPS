"""Publish the two charge sequences while keeping the shared release/counter assets closed."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('save.py')), init_globals={'RIDGE_PHASES': ('Charge',)})
