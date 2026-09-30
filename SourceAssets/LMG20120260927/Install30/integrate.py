import json,runpy
from pathlib import Path
O=Path(__file__).parent
receipt=O/'materials.json'
if not receipt.exists() or json.loads(receipt.read_text()).get('status')!='compiled_and_saved':
 runpy.run_path(str(O/'materials.py'),run_name='__main__')
runpy.run_path(str(O/'install.py'),run_name='__main__')
