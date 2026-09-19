"""Finish this already-submitted one-shot job; never submits or interrupts jobs."""
import json, time, subprocess, traceback
from pathlib import Path
from pipeline import req, P

tag='panoramic_red_dot_high'
pid=json.loads((P/(tag+'_submitted.json')).read_text())['prompt_id']
state=P/'job_status.json'
def save(status, **kw):
    state.write_text(json.dumps(dict(status=status,prompt_id=pid,updated_at=time.time(),**kw),indent=2))

try:
    deadline=time.time()+7200
    while time.time()<deadline:
        h=req('/history/'+pid)
        if pid in h:
            h=h[pid]
            (P/(tag+'_history.json')).write_text(json.dumps(h,indent=2))
            if h['status']['status_str']!='success':
                raise RuntimeError('ComfyUI job did not succeed; inspect saved history')
            break
        q=req('/queue')
        running=any(row[1]==pid for row in q['queue_running'])
        save('generating' if running else 'queued',pending_count=len(q['queue_pending']))
        time.sleep(45)
    else:
        save('waiting_timeout',note='Job not cancelled; inspect existing history before resuming.');raise SystemExit(2)
    save('downloading')
    subprocess.run([__import__('sys').executable,str(P/'fetch_models.py')],check=True,timeout=900)
    save('rendering')
    blender='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
    with (P/'render.log').open('w',encoding='utf-8') as log:
        subprocess.run([blender,'-b','--python',str(P/'render_models.py'),'--',tag],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    required=[P/(tag+s) for s in ['_mesh_report.json','_front.png','_back.png','_beauty.png','_candidate.blend']]
    assert all(f.exists() for f in required), 'Missing preview outputs; inspect render.log'
    save('generated_pending_visual_review',files=[f.name for f in required],note='Actual generated model; aperture and thin rim still require visual inspection. Not integrated into game.')
except Exception:
    save('failed',error=traceback.format_exc());raise
