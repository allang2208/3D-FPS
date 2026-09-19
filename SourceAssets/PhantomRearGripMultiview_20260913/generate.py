import json,sys,uuid,urllib.request,urllib.parse,subprocess
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
SEEDS=[91603,91627]
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
if sys.argv[1]=='submit':
    if not (P/'upload.json').exists():
        boundary=uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="phantom_grip_three_views.png"\r\nContent-Type: image/png\r\n\r\n').encode()+(P/'three_views.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
        up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
        (P/'upload.json').write_text(json.dumps(up))
    up=json.loads((P/'upload.json').read_text())
    info=json.loads((P/'generator_schema.json').read_text(encoding='utf-8-sig'))
    params={}
    for k,v in info['Trellis2MeshWithVoxelMultiViewGenerator']['input']['required'].items():
        if len(v)>1 and 'default' in v[1]:params[k]=v[1]['default']
        elif isinstance(v[0],list):params[k]=v[0][0]
    for seed in SEEDS:
        p=P/f'seed_{seed}';p.mkdir(exist_ok=True)
        if (p/'receipt.json').exists():continue
        w=json.loads(Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json').read_text())
        w['10']['inputs']['image']=up['name']
        for i in range(3):
            crop=str(110+i);pre=str(120+i)
            w[crop]={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':627*i,'y':0,'width':627,'height':836}}
            w[pre]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[crop,0],'padding':24,'remove_background':True,'max_size':2048}}
            w[str(130+i)]={'class_type':'SaveImage','inputs':{'images':[pre,0],'filename_prefix':f'PhantomGripMV/seed_{seed}/view{i}'}}
        pp=dict(params)
        pp.update(pipeline=['1',0],front_image=['120',0],left_image=['121',0],back_image=['122',0],seed=seed,pipeline_type='1024_cascade',sparse_structure_resolution=64,sparse_structure_steps=16,shape_steps=32,texture_steps=24,generate_texture_slat=True,fill_holes=False,keep_only_shell=False)
        w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':pp}
        w.pop('20',None)
        for key,name in [('51','raw'),('53','textured_master')]:w[key]['inputs']['filename_prefix']=f'PhantomGripMV/seed_{seed}/{name}'
        (p/'workflow.json').write_text(json.dumps(w,indent=2))
        r=req('/prompt',json.dumps({'client_id':'PhantomGripMV','prompt':w}).encode(),{'Content-Type':'application/json'})
        (p/'receipt.json').write_text(json.dumps(r,indent=2));print(seed,r,flush=True)
else:
    for seed in SEEDS:
        p=P/f'seed_{seed}';pid=json.loads((p/'receipt.json').read_text())['prompt_id']
        h=req('/history/'+pid).get(pid)
        if not h:print(seed,'pending',flush=True);continue
        (p/'history.json').write_text(json.dumps(h,indent=2))
        print(seed,h['status']['status_str'],flush=True)
        if h['status']['status_str']!='success':
            for kind,msg in h['status']['messages']:
                if kind=='execution_error':print(msg['exception_message'],flush=True)
            continue
        for filename in ['textured_master_00001_.glb','raw_00001_.glb']:
            if not (p/filename).exists():
                urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':f'PhantomGripMV/seed_{seed}','type':'output'}),p/filename)
        if not (p/'angle.png').exists():
            source=Path('D:/FPS3D/FPSGAME/SourceAssets/PhantomRearGripPixal_20260913/render_model.py').read_text()
            source=source.replace("('angle',(2,-3,1))", "('angle',(3,1.5,.7))")
            source=source.replace('PhantomRearGrip_Pixal_Editable.blend','PhantomRearGrip_Multiview_Editable.blend')
            (p/'render_model.py').write_text(source)
            with (p/'render.log').open('w') as log:
                subprocess.run(['E:/Program Files/Blender Foundation/Blender 5.1/blender.exe','-b','-t','8','--python',str(p/'render_model.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
            print(seed,'rendered',flush=True)
