"""Change only this task's still-queued wall-bank job to visible-front reconstruction.

The installed bank is embedded in the masonry/earth slope, so its hidden back is
not a fitting reference. The motor retains true multi-view generation. Never
cancel a running job or another task's queued job.
"""
import json,sys,urllib.request
raise RuntimeError('The entire dungeon 5080 batch was rejected on 2026-09-22; its outputs and job receipts are archived in project trash. Do not resubmit this bank.')
from pathlib import Path
import local_pipeline as p

root=Path(__file__).resolve().parents[1];folder=root/'Generated/buried_masonry_bank'
receipt=folder/'mesh_receipt.json'
old=json.loads(receipt.read_text());pid=old['prompt_id']
queue=p.request('/queue')
running={x[1] for x in queue.get('queue_running',[]) if isinstance(x,list) and len(x)>1}
pending={x[1] for x in queue.get('queue_pending',[]) if isinstance(x,list) and len(x)>1}
if pid in running:raise RuntimeError('Bank already running; keep the existing job')
if pid in pending:
    req=urllib.request.Request(p.BASE+'/queue',json.dumps({'delete':[pid]}).encode(),{'Content-Type':'application/json'})
    with p.HTTP.open(req,timeout=25) as response:response.read()
elif '--resume-after-delete' not in sys.argv or p.request('/history/'+pid).get(pid):
    raise RuntimeError('Bank is no longer queued; preserve receipt')
for name in ('mesh_receipt.json','mesh_workflow.json'):
    path=folder/name;path.rename(folder/('superseded_multiview_'+name))
cfg=json.loads((root/'assets.json').read_text())
prop=next(x for x in cfg['props'] if x['id']=='buried_masonry_bank')
prop['use_single_front']=True
prop['view_note']+=' The game prop is embedded in a wall bank; generate from the exposed front only. Hidden sides/back are reconstructed, not an exact multiview match. Original queued multiview job was withdrawn before execution.'
(root/'assets.json').write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8')
p.mesh(prop,folder)
print('OWN_QUEUED_BANK_REPLACED',pid)
