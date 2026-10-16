"""Save mesh/material/icon and the dedicated cue in one editor asset batch."""
import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'install_assets.py'),run_name='__main__')
runpy.run_path(str(O/'import_audio.py'),run_name='__main__')
