from pathlib import Path
import json,numpy as np
r=Path(__file__).resolve().parent;j=json.loads((r.parent/'ReturnReview24/final_manifest.json').read_text())
for c in j['cases']:
 if not c.get('surfaces'):continue
 end=3.14 if c['empty'] else 3.5
 extra=[2.875,2.9,2.96,3.08,3.14,4.98] if c['empty'] else [3.125,3.15,3.33,3.78]
 c['samples']=sorted(set([round(float(v),4) for v in np.linspace(2.76,end,16)]+extra))
(r/'manifest.json').write_text(json.dumps(j,indent=2));print('CONTACT25_REVIEW_CASES',len(j['cases']))
