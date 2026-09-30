"""Targeted read-back of the saved belt correction; does not run gameplay."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).parent))
import repair as r

receipt = json.loads((r.O / 'delivery.json').read_text())
assert r.sha(r.BODY) == receipt['saved'][r.BODY]['sha256']
body = r.load(r.BODY)
result = r.inspect(r.read(body), body)
assert result['triangles_by_slot'] == receipt['candidate_geometry']['triangles_by_slot']
assert r.slots(body) == r.slots(r.load(r.CANDIDATE))
receipt['saved_body_readback'] = result
(r.O / 'delivery.json').write_text(json.dumps(receipt, indent=2))
print('BELT51_SAVED_BODY_READBACK', json.dumps(result['cells']), flush=True)
