"""Production import and catalog save only; no generation, PIE, rendering previews or gameplay tests."""
import runpy
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parent
runpy.run_path(str(SCRIPTS/'import_assets.py'),run_name='__main__')
runpy.run_path(str(SCRIPTS/'install.py'),run_name='__main__')
