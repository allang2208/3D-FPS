"""Save only the new animation assets when the current editor has the older DLL."""
import runpy
from pathlib import Path
module = runpy.run_path(str(Path(__file__).resolve().parent/'install_attacks.py'))
module['main'](bind_pool=False)
