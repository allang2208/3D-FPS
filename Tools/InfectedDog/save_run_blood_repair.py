"""Save both prepared fixes in one editor mutex batch."""
import runpy
from pathlib import Path
folder=Path(__file__).resolve().parent
runpy.run_path(str(folder/'repair_blood_stain.py'),run_name='__main__')
runpy.run_path(str(folder/'install_godot_run_natural.py'),run_name='__main__')
