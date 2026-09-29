import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'install.py'),run_name='__main__')
runpy.run_path(str(O/'check_saved_materials.py'),run_name='__main__')
