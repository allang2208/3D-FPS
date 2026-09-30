from pathlib import Path
import sys,json
sys.path.insert(0,str(Path(__file__).parent))
import install as m
r=json.loads((m.O/'delivery.json').read_text())
assert m.sha(m.BODY)==r['saved'][m.BODY]['sha256']
r['saved_body_readback']=m.check(m.load(m.BODY))
(m.O/'delivery.json').write_text(json.dumps(r,indent=2))
print('BELT52_SAVED_BODY_READBACK',r['saved_body_readback'],flush=True)
