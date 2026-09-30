import json,runpy
from pathlib import Path
O=Path(__file__).parent;surface=O.parent/'Surface32';receipt=surface/'delivery.json'
if not receipt.exists() or json.loads(receipt.read_text()).get('status')!='current_201_refined_and_saved':
 runpy.run_path(str(surface/'integrate.py'),run_name='__main__')
runpy.run_path(str(O/'install.py'),run_name='__main__')
