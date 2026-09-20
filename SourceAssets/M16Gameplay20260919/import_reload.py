"""Update only the two M16 reload animations in the running UE editor."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('import_assets.py')),
              init_globals={'M16_RELOAD_ONLY': True})
