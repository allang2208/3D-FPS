import runpy
from pathlib import Path
O=Path(__file__).parent
runpy.run_path(str(O/'stage.py'),run_name='__main__')
runpy.run_path(str(O/'capture_ue.py'),run_name='__main__')
