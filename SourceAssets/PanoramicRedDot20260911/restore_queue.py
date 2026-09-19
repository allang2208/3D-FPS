"""Restore backed-up pending jobs after service restart, keeping original IDs/order."""
import json
from pipeline import P,req
backup=json.loads((P/'queue_before_recovery.json').read_text(encoding='utf-8-sig'))
for row in backup['queue_pending']:
    pid=row[1]
    queue=req('/queue')
    existing={r[1] for r in queue['queue_running']+queue['queue_pending']}
    if pid in existing or pid in req('/history/'+pid):
        print('Already present:',pid);continue
    result=req('/prompt',json.dumps({'prompt_id':pid,'prompt':row[2],'extra_data':row[3]}).encode(),{'Content-Type':'application/json'})
    assert result['prompt_id']==pid,result
    print('Restored:',pid)
