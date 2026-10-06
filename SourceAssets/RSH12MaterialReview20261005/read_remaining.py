import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'read_targeted_details.py'),run_name='__main__')
runpy.run_path(str(O/'read_materials.py'),run_name='__main__')
