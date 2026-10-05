"""Compatibility entrypoint for the retained, unaccepted V9 prototype; old recipe is in trash."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent / 'CoherentV9' / 'install_ue.py'),run_name='__main__')
