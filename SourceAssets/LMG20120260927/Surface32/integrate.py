import json,runpy
from pathlib import Path
O=Path(__file__).parent
if not (O/'materials.json').exists() or json.loads((O/'materials.json').read_text()).get('status')!='compiled_and_saved':runpy.run_path(str(O/'materials.py'),run_name='__main__')
runpy.run_path(str(O/'install.py'),run_name='__main__')
