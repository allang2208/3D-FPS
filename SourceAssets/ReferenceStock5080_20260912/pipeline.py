"""Run the user's reference stock through the verified RTX 5080 multiview pipeline."""
import json,urllib.request,urllib.error,urllib.parse,uuid,sys,time,hashlib
from pathlib import Path
from PIL import Image
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
REMOTE='ReferenceStock20260912'
TAG='reference_stock_high'

def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=30))

def save(name,value):
    (P/name).write_text(json.dumps(value,indent=2),encoding='utf-8')

def defaults(info,name):
    result={}
    for k,v in info[name]['input']['required'].items():
        if len(v)>1 and 'default' in v[1]:result[k]=v[1]['default']
        elif isinstance(v[0],list):result[k]=v[0][0]
    return result

def submit():
    receipt=P/(TAG+'_submitted.json')
    if receipt.exists():
        print(receipt.read_text());return
    hardware=req('/system_stats');save('system_stats.json',hardware)
    assert any('RTX 5080' in d['name'] for d in hardware['devices']), 'Expected user-specified GPU'
    info=req('/object_info');save('nodes.json',info)
    queue=req('/queue');save('queue_before.json',queue)
    source=P/'model_views.png';width,height=Image.open(source).size
    bounds=json.loads((P/'view_crops.json').read_text())
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="reference_stock_20260912.png"\r\nContent-Type: image/png\r\n\r\n').encode()+source.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary});save('upload.json',up)
    w={'1':{'class_type':'Trellis2LoadModel','inputs':defaults(info,'Trellis2LoadModel')},'2':{'class_type':'LoadImage','inputs':{'image':up['name']}}}
    w['1']['inputs'].update(low_vram=True,keep_models_loaded=False,backend='sdpa',sparse_backend='xformers',conv_backend='flex_gemm',modelname='microsoft/TRELLIS.2-4B')
    for i,view in enumerate(bounds):
        crop=str(10+i);x,y,cw,ch=view['crop'];assert 0<=x<width and 0<=y<height and x+cw<=width and y+ch<=height
        w[crop]={'class_type':'ImageCrop','inputs':{'image':['2',0],'x':x,'y':y,'width':cw,'height':ch}}
        w[str(30+i)]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[crop,0],'padding':24,'remove_background':True,'max_size':2048}}
        w[str(20+i)]={'class_type':'SaveImage','inputs':{'images':[str(30+i),0],'filename_prefix':f'{REMOTE}/{TAG}_view{i}'}}
    params=defaults(info,'Trellis2MeshWithVoxelMultiViewGenerator')
    params.update(pipeline=['1',0],front_image=['30',0],right_image=['31',0],back_image=['32',0],pipeline_type='1024_cascade',seed=91227,sparse_structure_steps=16,shape_steps=32,texture_steps=24,max_num_tokens=999999,generate_texture_slat=True,fill_holes=False)
    w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':params}
    w['5']={'class_type':'Trellis2MeshWithVoxelToTrimesh','inputs':{'mesh':['4',0],'reorient_vertices':'90 degrees'}}
    w['6']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['5',0],'filename_prefix':f'{REMOTE}/{TAG}_raw_geometry','file_format':'glb'}}
    w['7']={'class_type':'Trellis2OvoxelExportToGLB','inputs':{'mesh':['4',0],'resolution':1024,'texture_size':4096,'target_face_num':200000}}
    w['8']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['7',0],'filename_prefix':f'{REMOTE}/{TAG}_textured_master','file_format':'glb'}}
    save(TAG+'_workflow.json',w)
    try:r=req('/prompt',json.dumps({'client_id':REMOTE,'prompt':w}).encode(),{'Content-Type':'application/json'})
    except urllib.error.HTTPError as e:print(e.read().decode());raise
    r.update(submitted_at=time.time(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    save(TAG+'_submitted.json',r);print(json.dumps(r))

def status():
    pid=json.loads((P/(TAG+'_submitted.json')).read_text())['prompt_id']
    h=req('/history/'+pid)
    if pid not in h:
        q=req('/queue');print(json.dumps({'status':'pending','running':[x[1] for x in q['queue_running']],'queued':[x[1] for x in q['queue_pending']]}));return
    save(TAG+'_history.json',h[pid]);print(json.dumps(h[pid]['status']))

if __name__=='__main__':
    (submit if sys.argv[1]=='submit' else status)()
