"""Background asset publication only; uses the existing editor binary, never starts PIE."""
import runpy
from pathlib import Path
P=Path(__file__).resolve().parent
runpy.run_path(str(P/'import_modules.py'),run_name='__main__')
runpy.run_path(str(P/'import_icons.py'),run_name='__main__')
