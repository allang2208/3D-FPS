import json,urllib.request
from pathlib import Path
P=Path(__file__).parent
w=json.loads((P/'workflow.json').read_text())
w['8']['inputs']['value']=.76
w['6']['inputs']['filename_prefix']='PrismCompare20260910/prism_fixed'
w['11']['inputs']['filename_prefix']='PrismCompare20260910/input_fixed'
(P/'workflow_fixed.json').write_text(json.dumps(w,indent=2))
assert not (P/'submitted_fixed.json').exists()
r=json.load(urllib.request.urlopen(urllib.request.Request('http://192.168.3.142:8188/prompt',data=json.dumps({'client_id':'prism-fixed-mask-20260910','prompt':w}).encode(),headers={'Content-Type':'application/json'}),timeout=30))
(P/'submitted_fixed.json').write_text(json.dumps(r,indent=2));print(r)
