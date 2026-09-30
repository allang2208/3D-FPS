"""Run dependent material and mesh authoring within one UE authoring batch."""
import json, runpy
from pathlib import Path
root = Path(__file__).parent
receipt = root / 'materials_receipt.json'
if not receipt.exists() or json.loads(receipt.read_text()).get('status') != 'materials_compiled_and_saved':
    runpy.run_path(str(root / 'materials.py'), run_name='__main__')
runpy.run_path(str(root / 'install.py'), run_name='__main__')
