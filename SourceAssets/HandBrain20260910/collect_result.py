import json
import hashlib
from pathlib import Path
import requests

root=Path(__file__).resolve().parent
base='http://127.0.0.1:18189'
pid=json.loads((root/'submission.json').read_text())['prompt_id']
r=requests.get(base+'/history/'+pid,timeout=30)
r.raise_for_status()
result=r.json().get(pid)
if not result:
    print('RUNNING')
    raise SystemExit(0)
(root/('history_'+pid+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result['status'],ensure_ascii=True))
if result['status']['status_str'] != 'success':
    raise SystemExit(1)
print(json.dumps(result['outputs'],ensure_ascii=True))
files=[]
def walk(obj):
    if isinstance(obj,dict):
        if 'filename' in obj:
            files.append(obj)
        else:
            for v in obj.values(): walk(v)
    elif isinstance(obj,list):
        for v in obj: walk(v)
walk(result['outputs'])
for item in files:
    name=Path(item['filename']).name
    if name.endswith('.glb'):
        name='handbrain_detailed_v01.glb'
    response=requests.get(base+'/view',params={k:item[k] for k in ('filename','subfolder','type') if k in item},timeout=120)
    response.raise_for_status()
    (root/name).write_bytes(response.content)
    print('Downloaded',name,len(response.content),hashlib.sha256(response.content).hexdigest())
