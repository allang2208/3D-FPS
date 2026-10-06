"""One bridge batch for this task's mesh/materials and framed UI texture."""
import runpy
from pathlib import Path
O = Path(__file__).resolve().parent
runpy.run_path(str(O / 'import_assets.py'), run_name='__main__')
runpy.run_path(str(O / 'import_icon.py'), run_name='__main__')
