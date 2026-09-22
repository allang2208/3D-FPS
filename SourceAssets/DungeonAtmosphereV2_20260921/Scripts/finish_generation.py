"""Wait for this finite four-prop batch, download each result and adapt it.

Only this task's recorded prompt IDs are read. Never clears or cancels queues.
Run in the current production turn; this is not a scheduled monitor.
"""
import json
import subprocess
import time
from pathlib import Path
import local_pipeline as pipeline

ROOT=Path(__file__).resolve().parents[1]
blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
pending={p['id'] for p in pipeline.CFG['props'] if not (ROOT/'Generated'/p['id']/'Game/asset-manifest.json').exists()}
deadline=time.monotonic()+3600
while pending:
    if time.monotonic()>deadline:raise RuntimeError('Owned generation batch still running after one hour; receipts preserved')
    newly_ready=[]
    for ident in sorted(pending):
        folder=ROOT/'Generated'/ident
        pid=json.loads((folder/'mesh_receipt.json').read_text())['prompt_id']
        history=pipeline.request('/history/'+pid).get(pid)
        if not history:continue
        status=history.get('status',{}).get('status_str')
        if status!='success':raise RuntimeError('Owned generation failed: '+ident+' '+str(status))
        pipeline.fetch(folder,'mesh');newly_ready.append(ident)
    if newly_ready:
        subprocess.run([blender,'--background','--factory-startup','--threads','8','--python',str(ROOT/'Scripts/refine_generated.py')],check=True)
        for ident in newly_ready:
            pending.remove(ident);print('PRODUCTION_READY',ident,flush=True)
    if pending:
        print('GENERATION_WAITING',', '.join(sorted(pending)),flush=True)
        time.sleep(40)
print('ALL_FOUR_PROPS_READY_FOR_UE',flush=True)
