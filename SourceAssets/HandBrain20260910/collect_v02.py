import json
from pathlib import Path
import requests
root=Path(__file__).resolve().parent/'v02'
base='http://127.0.0.1:18189'
pid=json.loads((root/'submission.json').read_text())['prompt_id']
response=requests.get(base+'/history/'+pid,timeout=30)
response.raise_for_status()
result=response.json().get(pid)
if not result:
    print('RUNNING')
    raise SystemExit(0)
(root/'history.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result['status']))
if result['status']['status_str']!='success': raise SystemExit(1)
response=requests.get(base+'/view',params={'filename':'handbrain_detailed_v02_00001_.glb','subfolder':'HandBrain20260910','type':'output'},timeout=120)
response.raise_for_status()
(root/'handbrain_detailed_v02.glb').write_bytes(response.content)
print('Downloaded',len(response.content),'bytes')
