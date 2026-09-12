"""Package current CMU metadata; never restore old attacks or run new tests."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('finalize_mocap_delivery.py')), run_name='__main__')
