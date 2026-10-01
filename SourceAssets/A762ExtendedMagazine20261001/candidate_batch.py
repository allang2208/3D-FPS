import runpy
from pathlib import Path
folder = Path(__file__).parent
runpy.run_path(str(folder / 'install_candidate.py'))
runpy.run_path(str(folder / 'read_build.py'))
runpy.run_path(str(folder / 'capture_candidate.py'))
