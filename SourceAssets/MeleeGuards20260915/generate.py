import json,sys,uuid,urllib.request,urllib.parse
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
designs=json.loads((P/'designs.json').read_text(encoding='utf-8'))
for d in designs:
    folder=P/d['id'];receipt=folder/'receipt.json'
    if sys.argv[1]=='submit':
        if receipt.exists():
            print(d['id'],'already submitted',flush=True);continue
        boundary=uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="frost_{d["id"]}_three_views.png"\r\nContent-Type: image/png\r\n\r\n').encode()+(folder/'three_views.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
        upload=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
        (folder/'upload.json').write_text(json.dumps(upload,indent=2))
        w=json.loads(Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json').read_text())
        w['10']['inputs']['image']=upload['name']
        for key in ['11','12','20','21','22']:w.pop(key,None)
        crops=[(0,280,650,400),(675,280,200,400),(895,280,641,400)]
        for i,(x,y,width,height) in enumerate(crops):
            crop=str(110+i);pre=str(120+i)
            w[crop]={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':x,'y':y,'width':width,'height':height}}
            w[pre]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[crop,0],'padding':24,'remove_background':True,'max_size':2048}}
            w[str(130+i)]={'class_type':'SaveImage','inputs':{'images':[pre,0],'filename_prefix':f'MeleeGuards20260915/{d["id"]}/view{i}'}}
        schema=json.loads((P/'Trellis2MeshWithVoxelMultiViewGenerator.json').read_text(encoding='utf-8-sig'))['Trellis2MeshWithVoxelMultiViewGenerator']['input']['required']
        pp={}
        for k,v in schema.items():
            if len(v)>1 and 'default' in v[1]:pp[k]=v[1]['default']
            elif isinstance(v[0],list):pp[k]=v[0][0]
        pp.update(pipeline=['1',0],front_image=['120',0],left_image=['121',0],back_image=['122',0],seed=d['seed'],pipeline_type='1024_cascade',sparse_structure_resolution=64,sparse_structure_steps=16,shape_steps=32,texture_steps=24,generate_texture_slat=True,fill_holes=False,keep_only_shell=False)
        w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':pp}
        for key,name in [('51','raw'),('53','textured_master')]:w[key]['inputs']['filename_prefix']=f'MeleeGuards20260915/{d["id"]}/{name}'
        (folder/'workflow.json').write_text(json.dumps(w,indent=2))
        r=req('/prompt',json.dumps({'client_id':'MeleeGuards20260915','prompt':w}).encode(),{'Content-Type':'application/json'})
        receipt.write_text(json.dumps(r,indent=2));print(d['id'],r,flush=True)
    else:
        if not receipt.exists():continue
        pid=json.loads(receipt.read_text())['prompt_id'];h=req('/history/'+pid).get(pid)
        if not h:print(d['id'],'pending',flush=True);continue
        (folder/'history.json').write_text(json.dumps(h,indent=2))
        print(d['id'],h['status']['status_str'],flush=True)
        if h['status']['status_str']!='success':
            for kind,msg in h['status']['messages']:
                if kind=='execution_error':print(msg['exception_message'],flush=True)
            continue
        for filename in ['textured_master_00001_.glb','raw_00001_.glb']:
            if not (folder/filename).exists():
                urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':f'MeleeGuards20260915/{d["id"]}','type':'output'}),folder/filename)
                print(d['id'],'downloaded',filename,flush=True)
