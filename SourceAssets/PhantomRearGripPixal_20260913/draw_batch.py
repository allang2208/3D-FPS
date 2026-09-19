import json,sys,time,urllib.request,urllib.parse,subprocess
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
def req(path,data=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json'}),timeout=45))
seeds=[91317,91337,91361,91403,91427,91451]
if sys.argv[1]=='submit':
    for seed in seeds:
        p=P/f'seed_{seed}';p.mkdir(exist_ok=True)
        if (p/'receipt.json').exists():continue
        w=json.loads((P/'workflow.json').read_text())
        w['4']['inputs']['seed']=seed
        if seed >= 91400:
            w['4']['inputs']['shape_guidance_strength']=9.0
            w['4']['inputs']['shape_steps']=40
        for key in ['51','53','21']:
            w[key]['inputs']['filename_prefix']=f'PhantomRearGripDraws/seed_{seed}/'+{'51':'raw','53':'textured_master','21':'input'}[key]
        (p/'workflow.json').write_text(json.dumps(w,indent=2))
        r=req('/prompt',{'client_id':'PhantomRearGripDraws','prompt':w})
        (p/'receipt.json').write_text(json.dumps(r,indent=2));print(seed,r,flush=True)
else:
    for seed in seeds:
        p=P/f'seed_{seed}'
        pid=json.loads((p/'receipt.json').read_text())['prompt_id']
        h=req('/history/'+pid).get(pid)
        if not h:print(seed,'pending',flush=True);continue
        (p/'history.json').write_text(json.dumps(h,indent=2))
        print(seed,h['status']['status_str'],flush=True)
        if h['status']['status_str']!='success':
            for kind,msg in h['status']['messages']:
                if kind=='execution_error':print(msg['exception_message'],flush=True)
            continue
        if not (p/'textured_master_00001_.glb').exists():
            url=BASE+'/view?'+urllib.parse.urlencode({'filename':'textured_master_00001_.glb','subfolder':f'PhantomRearGripDraws/seed_{seed}','type':'output'})
            urllib.request.urlretrieve(url,p/'textured_master_00001_.glb')
        if not (p/'angle.png').exists():
            script=(P/'render_model.py').read_text()
            (p/'render_model.py').write_text(script)
            with (p/'render.log').open('w') as log:
                subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','-t','8','--python',str(p/'render_model.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
            print(seed,'rendered',flush=True)
