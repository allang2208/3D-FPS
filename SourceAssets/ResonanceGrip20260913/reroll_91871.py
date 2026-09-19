import json,urllib.request,urllib.parse,sys
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ResonanceGrip20260913'); seed=91871; C=P/f'seed_{seed}'; C.mkdir(exist_ok=True)
base='http://192.168.3.142:8188'
if sys.argv[1]=='submit':
 w=json.loads((P/'seed_91813/workflow.json').read_text())
 w['4']['inputs']['seed']=seed
 for node in w.values():
  if 'filename_prefix' in node.get('inputs',{}): node['inputs']['filename_prefix']=node['inputs']['filename_prefix'].replace('seed_91813',f'seed_{seed}')
 (C/'workflow.json').write_text(json.dumps(w,indent=2))
 if not (C/'receipt.json').exists():
  req=urllib.request.Request(base+'/prompt',data=json.dumps({'client_id':'ResonanceReroll','prompt':w}).encode(),headers={'Content-Type':'application/json'})
  r=json.load(urllib.request.urlopen(req,timeout=60)); (C/'receipt.json').write_text(json.dumps(r,indent=2)); print(r)
else:
 pid=json.loads((C/'receipt.json').read_text())['prompt_id']; h=json.load(urllib.request.urlopen(base+'/history/'+pid,timeout=60)).get(pid)
 if not h: print('pending'); sys.exit()
 (C/'history.json').write_text(json.dumps(h,indent=2)); print(h['status']['status_str'])
 if h['status']['status_str']=='success':
  for f in ['raw_00001_.glb','textured_master_00001_.glb']:
   if not (C/f).exists(): urllib.request.urlretrieve(base+'/view?'+urllib.parse.urlencode({'filename':f,'subfolder':f'ResonanceGripMV/seed_{seed}','type':'output'}),C/f)
   print(C/f)
 else: print(h['status']['messages'])

