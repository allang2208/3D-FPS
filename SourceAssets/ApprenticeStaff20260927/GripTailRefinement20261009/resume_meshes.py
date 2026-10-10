"""Resume the mesh transfer after materials and palette were saved successfully."""
import runpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
receipt=json.loads((P/'install-receipt.json').read_text(encoding='utf-8'))
(P/'materials-saved-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
runpy.run_path(str(P/'install_ue.py'),init_globals={'RESUME_SAVED_MATERIALS':True})
