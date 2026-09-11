import json, urllib.request, urllib.parse, urllib.error, uuid, sys, time, os
from pathlib import Path
from PIL import Image
P=Path(__file__).parent
BASE=os.environ.get('COMFY_BASE_URL','http://192.168.3.142:8188')
REMOTE='PanoramicRedDot20260911'
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
def defaults(info,name):
    result={}
    for k,v in info[name]['input']['required'].items():
        if len(v)>1 and 'default' in v[1]: result[k]=v[1]['default']
        elif isinstance(v[0],list): result[k]=v[0][0]
    return result
def submit(asset,quality):
    tag=asset+'_'+quality; receipt=P/(tag+'_submitted.json')
    if receipt.exists(): print(receipt.read_text()); return
    info=json.loads((P/'nodes.json').read_text(encoding='utf-8-sig'))
    source=P/(asset+'_three_views.png'); width,height=Image.open(source).size
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{asset}_20260911.png"\r\nContent-Type: image/png\r\n\r\n').encode()+source.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    w={'1':{'class_type':'Trellis2LoadModel','inputs':defaults(info,'Trellis2LoadModel')},'2':{'class_type':'LoadImage','inputs':{'image':up['name']}}}
    w['1']['inputs'].update(low_vram=True,keep_models_loaded=False,backend='sdpa',sparse_backend='xformers',conv_backend='flex_gemm',modelname='microsoft/TRELLIS.2-4B')
    for i in range(3):
        crop=str(10+i)
        w[crop]={'class_type':'ImageCrop','inputs':{'image':['2',0],'x':i*(width//3),'y':0,'width':width//3,'height':height}}
        w[str(20+i)]={'class_type':'SaveImage','inputs':{'images':[crop,0],'filename_prefix':f'{REMOTE}/{tag}_view{i}'}}
    high=quality=='high'; v=defaults(info,'Trellis2MeshWithVoxelMultiViewGenerator')
    v.update(pipeline=['1',0],front_image=['10',0],right_image=['11',0],back_image=['12',0],pipeline_type='1024_cascade' if high else '512',seed=91143,sparse_structure_steps=16 if high else 12,shape_steps=32 if high else 16,texture_steps=24 if high else 12,max_num_tokens=999999 if high else 49152,generate_texture_slat=True,fill_holes=False)
    w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':v}
    w['5']={'class_type':'Trellis2MeshWithVoxelToTrimesh','inputs':{'mesh':['4',0],'reorient_vertices':'90 degrees'}}
    w['6']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['5',0],'filename_prefix':f'{REMOTE}/{tag}_raw_geometry','file_format':'glb'}}
    # Equal texture and export budgets isolate reconstruction quality from export detail.
    w['7']={'class_type':'Trellis2OvoxelExportToGLB','inputs':{'mesh':['4',0],'resolution':1024 if high else 512,'texture_size':2048,'target_face_num':100000}}
    w['8']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['7',0],'filename_prefix':f'{REMOTE}/{tag}_textured_master','file_format':'glb'}}
    (P/(tag+'_workflow.json')).write_text(json.dumps(w,indent=2))
    try: result=req('/prompt',json.dumps({'client_id':'panoramic-red-dot-20260911','prompt':w}).encode(),{'Content-Type':'application/json'})
    except urllib.error.HTTPError as e: print(e.read().decode()); raise
    result['submitted_at']=time.time(); receipt.write_text(json.dumps(result,indent=2)); print(result)
def status(asset,quality):
    tag=asset+'_'+quality; pid=json.loads((P/(tag+'_submitted.json')).read_text())['prompt_id']
    h=req('/history/'+pid)
    if pid not in h: print(tag,'pending'); return
    h=h[pid]; (P/(tag+'_history.json')).write_text(json.dumps(h,indent=2))
    print(tag,h['status'])
def download(filename):
    target=P/Path(filename).name
    urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':REMOTE,'type':'output'}),target)
    print(target.name,target.stat().st_size)
if __name__=='__main__':
    if sys.argv[1]=='download': download(sys.argv[2])
    else: (submit if sys.argv[1]=='submit' else status)(sys.argv[2],sys.argv[3])
