"""Only read transient mesh copies; never load maps, change actors or stop PIE."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('doorway_read.py')),init_globals={'MESHES_ONLY':True,'OUTPUT_NAME':'doorways-after-live.json'})
