import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('read_saved.py')),init_globals={'READ_VERSION':'after'})
