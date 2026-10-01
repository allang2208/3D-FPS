"""Save only the new parent while another checkout uses the shared old instance."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('apply_finish.py')), init_globals={'PREPARE_ONLY': True})
