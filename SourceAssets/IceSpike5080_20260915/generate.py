"""Submit one actual three-view TRELLIS candidate; fetch without any render or test."""
import json, sys, uuid, urllib.request, urllib.parse
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
SEED=91571
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=50))
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
p=P/f'seed_{SEED}';p.mkdir(exist_ok=True)
if sys.argv[1]=='submit':
    if (p/'receipt.json').exists():
        print('Already submitted:',(p/'receipt.json').read_text());sys.exit(0)
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="ice_spike_three_views_20260915.png"\r\nContent-Type: image/png\r\n\r\n').encode()+(P/'three_views.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary});dump(P/'upload.json',up)
    w=json.loads((P/'trellis-multiview.api.json').read_text())
    w['10']['inputs']['image']=up['name']
    for key in ['11','12','20','21','22']:w.pop(key,None)
    for i,view in enumerate(['front','right','back']):
        crop=str(110+i);pre=str(120+i)
        w[crop]={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':512*i,'y':0,'width':512,'height':1024}}
        w[pre]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[crop,0],'padding':24,'remove_background':True,'max_size':2048}}
        w[str(130+i)]={'class_type':'SaveImage','inputs':{'images':[pre,0],'filename_prefix':f'IceSpike5080/seed_{SEED}/{view}'}}
    w['4']['inputs'].update(front_image=['120',0],right_image=['121',0],back_image=['122',0],seed=SEED,fill_holes=True,keep_only_shell=True)
    for key,name in [('51','raw'),('53','textured_master')]:w[key]['inputs']['filename_prefix']=f'IceSpike5080/seed_{SEED}/{name}'
    dump(p/'workflow.json',w)
    r=req('/prompt',json.dumps({'client_id':'IceSpike5080_20260915','prompt':w}).encode(),{'Content-Type':'application/json'})
    dump(p/'receipt.json',r);print(json.dumps(r),flush=True)
else:
    pid=json.loads((p/'receipt.json').read_text())['prompt_id'];h=req('/history/'+pid).get(pid)
    if not h:
        q=req('/queue');print(json.dumps({'status':'pending','running_ids':[x[1] for x in q['queue_running']],'pending_ids':[x[1] for x in q['queue_pending']]}));sys.exit(0)
    dump(p/'history.json',h);print(h['status']['status_str'],flush=True)
    if h['status']['status_str']!='success':
        print(json.dumps(h['status']['messages'])[-6000:]);sys.exit(1)
    for filename in ['textured_master_00001_.glb','raw_00001_.glb','front_00001_.png','right_00001_.png','back_00001_.png']:
        if not (p/filename).exists():
            urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':f'IceSpike5080/seed_{SEED}','type':'output'}),p/filename)
        print(filename,(p/filename).stat().st_size,flush=True)
