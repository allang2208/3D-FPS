import runpy
from pathlib import Path
folder = Path(__file__).parent
runpy.run_path(str(folder / 'read_build.py'))
runpy.run_path(str(folder / 'capture_saved.py'))
