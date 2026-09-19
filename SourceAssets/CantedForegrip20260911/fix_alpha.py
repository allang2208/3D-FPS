import json,urllib.request,shutil
from pathlib import Path
O=Path(__file__).parent
for n in ['request.json','receipt.json','history.json']:shutil.copy2(O/n,O/('rejected_cube_'+n))
r=json.loads((O/'request.json').read_text());r['prompt']['9']['inputs']['alpha']=['2',1];r['prompt'].pop('8');r['client_id']='canted-alpha-fixed-20260911'
(O/'request.json').write_text(json.dumps(r,indent=2));a=json.load(urllib.request.urlopen(urllib.request.Request('http://192.168.3.142:8188/prompt',data=json.dumps(r).encode(),headers={'Content-Type':'application/json'}),timeout=30));(O/'receipt.json').write_text(json.dumps(a,indent=2));print(a)
