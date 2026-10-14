import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('doorway_read.py')),init_globals={'OUTPUT_NAME':'doorways-after.json'})
