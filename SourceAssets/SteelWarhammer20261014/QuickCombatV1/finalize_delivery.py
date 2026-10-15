"""Record only actual saved-animation and formal-build completion."""
from pathlib import Path
from datetime import datetime
import json
P=Path(__file__).resolve().parent
imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
built=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision']!='ShaftCheckV1_20261015':raise RuntimeError('Animation save is incomplete')
if not built['complete'] or any(x['exit_code']!=0 for x in built['targets']):raise RuntimeError('Formal builds are incomplete')
receipt={'revision':imported['revision'],'saved_assets':imported['saved'],'builds':built['targets'],
         'seconds':.5,'contact_seconds':.15,'finished':datetime.now().isoformat(timespec='seconds'),
         'runtime_tested':False,'multiplayer_tested':False,'preview_rendered':False}
(P/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
