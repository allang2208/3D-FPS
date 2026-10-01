import runpy
from pathlib import Path
p=Path(__file__).parent
for s in ('export_inputs.py','export_bones.py'):runpy.run_path(str(p/s),run_name='__main__')
