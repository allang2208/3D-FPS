"""Import only the M16 empty-reload charging-handle animation."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('import_assets.py')),
              init_globals={'M16_EMPTY_ONLY': True})
