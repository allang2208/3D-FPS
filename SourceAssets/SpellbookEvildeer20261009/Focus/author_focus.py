"""Save V30 natural opening/contact opening/recover; run with background Blender."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'IntegratedV30/save_editable.py'),run_name='__main__')
