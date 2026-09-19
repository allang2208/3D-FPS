"""Read-only sampler progress; exits before another queued task starts."""
import json,subprocess,time,urllib.request
from pathlib import Path
P=Path(__file__).parent
PID=json.loads((P/'magic_dust_high_recovery_submitted.json').read_text(encoding='utf-8-sig'))['prompt_id']
while True:
 q=json.load(urllib.request.urlopen('http://192.168.3.142:8188/queue',timeout=15))
 if not any(row[1]==PID for row in q['queue_running']):break
 raw=subprocess.check_output(['ssh','-o','BatchMode=yes','r5080','D:/开发文件/ComfyUI/output/EnhancementMaterials20260911/py-spy-enhancement-audit.exe','dump','--pid','25256','--nonblocking','--locals','--json'],timeout=30)
 result={'time':time.time()}
 for thread in json.loads(raw):
  for frame in thread['frames']:
   if 'flow_euler.py' in frame.get('filename','') and frame.get('name')=='sample':
    v={v['name']:v['repr'] for v in frame.get('locals',[]) if v['name'] in ('t','t_prev','steps','tqdm_desc','rescale_t')}
    if 't' in v:
     result.update(v);t=float(v['t']);r=float(v.get('rescale_t',1));steps=int(v['steps'])
     result['current_step']=round((1-t/(r-t*(r-1)))*steps)+1
 with (P/'recovery_progress.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
 print(result,flush=True);time.sleep(60)
