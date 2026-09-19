import json,time,subprocess,sys
from pathlib import Path
P=Path(__file__).parent
for attempt in range(240):
 r=subprocess.run([sys.executable,'-X','utf8',str(P/'status_download.py')],cwd=P,capture_output=True,text=True,encoding='utf-8')
 with (P/'automatic_delivery.log').open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' '+r.stdout+r.stderr+'\n')
 h=P/'history.json'
 if h.exists():
  status=next(iter(json.loads(h.read_text()).values()))['status']
  if status['status_str']=='error':sys.exit(1)
  if r.returncode==0 and list(P.glob('*textured*.glb')):
   with (P/'render.log').open('w',encoding='utf-8') as log:
    x=subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','-t','4','--python',str(P/'render_candidate.py')],stdout=log,stderr=subprocess.STDOUT)
   if x.returncode!=0:sys.exit(x.returncode)
   (P/'DELIVERY_COMPLETE.json').write_text(json.dumps({'generated':True,'rendered':True,'editable_blend':str(P/'VerticalForegrip_5080_Editable.blend'),'stage':'Generated candidate only; not game integrated'},indent=2));sys.exit()
 time.sleep(30)
raise RuntimeError('Queue wait exceeded 2 hours; generation remains on server; inspect receipt')
