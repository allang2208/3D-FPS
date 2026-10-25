"""Save only the two revised exits, for both supported player bodies."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('save_chair_reuse.py')),
               init_globals={'FURNITURE_REVISION': 'ArmrestExit20261024'})
runpy.run_path(str(Path(__file__).with_name('read_armrest_exit_saved.py')))
