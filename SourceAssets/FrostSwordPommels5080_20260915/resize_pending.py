"""Apply the user's 512 geometry preference to only our two queued jobs."""
import json, shutil, sys, urllib.request
from pathlib import Path
P=Path(__file__).parent
B='http://192.168.3.142:8188'
def request(path, body=None):
    data=None if body is None else json.dumps(body).encode()
    payload=urllib.request.urlopen(urllib.request.Request(B+path,data=data,headers={'Content-Type':'application/json'}),timeout=60).read()
    return json.loads(payload) if payload else {}
keys=['ballast_rune','ballast_magic_orb']
receipts={key:json.loads((P/key/'receipt.json').read_text()) for key in keys}
queue=request('/queue')
pending={row[1] for row in queue['queue_pending']}
running={row[1] for row in queue['queue_running']}
resume='--resume-after-delete' in sys.argv
if resume:
    if any(r['prompt_id'] in pending|running for r in receipts.values()):
        raise RuntimeError('Deleted jobs are still active; no jobs submitted.')
elif not all(r['prompt_id'] in pending for r in receipts.values()):
    raise RuntimeError('Expected two owned queued jobs; no queue changed.')
for key in keys:
    folder=P/key
    archive=folder/'ss32_cascade_queued_attempt'
    archive.mkdir(exist_ok=True)
    if not resume:
        for name in ('workflow.json','receipt.json'):
            shutil.copy2(folder/name,archive/name)
if not resume:
    request('/queue',{'delete':[r['prompt_id'] for r in receipts.values()]})
for key in keys:
    folder=P/key
    w=json.loads((folder/'workflow.json').read_text())
    w['4']['inputs']['pipeline_type']='512'
    for node,name in [('51','raw'),('53','textured_master')]:
        w[node]['inputs']['filename_prefix']=f'FrostSwordPommels5080_20260915/ss32_512/{key}/{name}'
    (folder/'workflow.json').write_text(json.dumps(w,indent=2))
    receipt=request('/prompt',{'client_id':'FrostSwordPommels5080_20260915','prompt':w})
    receipt['attempt']='ss32_512_user_selected'
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
    print(key,receipt,flush=True)
