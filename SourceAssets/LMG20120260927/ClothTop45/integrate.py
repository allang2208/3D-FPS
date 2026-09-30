from pathlib import Path
import runpy
O=Path(__file__).parent
runpy.run_path(str(O/'materials.py'),run_name='__main__')
runpy.run_path(str(O/'install.py'),run_name='__main__')
