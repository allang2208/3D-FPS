import json, time
from pipeline import P, req
while True:
    queue=req('/queue')
    active=[row[1] for row in queue['queue_running']]
    sample={'time':time.time(),'running':active,'devices':req('/system_stats')['devices']}
    with (P/'vram_samples.jsonl').open('a') as f: f.write(json.dumps(sample)+'\n')
    done=[]
    for receipt in P.glob('*_submitted.json'):
        pid=json.loads(receipt.read_text())['prompt_id']; h=req('/history/'+pid)
        if pid in h:
            (P/receipt.name.replace('_submitted','_history')).write_text(json.dumps(h[pid],indent=2))
            done.append(receipt.stem.replace('_submitted','')+':'+h[pid]['status']['status_str'])
    print(json.dumps({'running':active,'pending':len(queue['queue_pending']),'done':done}),flush=True)
    if len(done)==4: break
    time.sleep(20)
