"""One queued UE batch: repair the identified inheritance gap, reload, then capture."""
import runpy
from pathlib import Path
O=Path(__file__).resolve().parent
runpy.run_path(str(O/'repair.py'),run_name='__main__')
runpy.run_path(str(O/'read_inputs.py'),run_name='__main__')
runpy.run_path(str(O/'capture_frames.py'),run_name='__main__')
