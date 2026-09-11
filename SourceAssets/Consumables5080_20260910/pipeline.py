import json, urllib.request, urllib.parse, uuid, sys
from pathlib import Path
from PIL import Image
P=Path(__file__).parent
BASE='http://127.0.0.1:18189'
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
def defaults(info,name):
    result={}
    for k,v in info[name]['input']['required'].items():
        if len(v)>1 and 'default' in v[1]: result[k]=v[1]['default']
        elif isinstance(v[0],list): result[k]=v[0][0]
    return result
def submit(asset):
    receipt=P/(asset+'_submitted.json')
    if receipt.exists(): print(receipt.read_text());return
    info=json.loads((P.parents[1]/'Saved/consumable_nodes.json').read_text(encoding='utf-8-sig'))
    source=P/(asset+'_three_views.png'); width,height=Image.open(source).size
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="consumable_{asset}_20260910.png"\r\nContent-Type: image/png\r\n\r\n').encode()+source.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    up=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    w={'1':{'class_type':'Trellis2LoadModel','inputs':defaults(info,'Trellis2LoadModel')},'2':{'class_type':'LoadImage','inputs':{'image':up['name']}}}
    w['1']['inputs'].update(low_vram=True,keep_models_loaded=False,backend='sdpa',sparse_backend='xformers',conv_backend='flex_gemm',modelname='microsoft/TRELLIS.2-4B')
    for i in range(3):
        crop=str(10+i*3);pre=str(11+i*3);save=str(12+i*3)
        w[crop]={'class_type':'ImageCrop','inputs':{'image':['2',0],'x':i*(width//3),'y':0,'width':width//3,'height':height}}
        w[pre]={'class_type':'ImageCrop','inputs':{'image':[crop,0],'x':4,'y':4,'width':width//3-8,'height':height-8}}
        w[save]={'class_type':'SaveImage','inputs':{'images':[pre,0],'filename_prefix':f'Consumables20260910/{asset}_view{i}'}}
    v=defaults(info,'Trellis2MeshWithVoxelMultiViewGenerator')
    v.update(pipeline=['1',0],front_image=['11',0],right_image=['14',0],back_image=['17',0],pipeline_type='512',seed=91050+['hp_potion','mp_potion','ammo_556','ammo_762'].index(asset),shape_steps=16,texture_steps=12,max_num_tokens=49152,generate_texture_slat=True,fill_holes=False)
    w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':v}
    w['5']={'class_type':'Trellis2OvoxelExportToGLB','inputs':{'mesh':['4',0],'resolution':512,'texture_size':2048,'target_face_num':20000}}
    w['6']={'class_type':'Trellis2ExportMesh','inputs':{'trimesh':['5',0],'filename_prefix':f'Consumables20260910/{asset}_candidate_v01','file_format':'glb'}}
    (P/(asset+'_workflow.json')).write_text(json.dumps(w,indent=2))
    try: result=req('/prompt',json.dumps({'client_id':'consumables-20260910','prompt':w}).encode(),{'Content-Type':'application/json'})
    except urllib.error.HTTPError as e: print(e.read().decode());raise
    receipt.write_text(json.dumps(result,indent=2));print(result)
def status(asset):
    receipt=json.loads((P/(asset+'_submitted.json')).read_text()); pid=receipt['prompt_id']
    h=req('/history/'+pid)
    if pid not in h: print(asset,'pending');return
    h=h[pid];(P/(asset+'_history.json')).write_text(json.dumps(h,indent=2))
    print(asset,h['status'])
    for node,out in h.get('outputs',{}).items():
        print(node,out)
        for key,items in out.items():
            if isinstance(items,list):
                for entry in items:
                    if isinstance(entry,dict) and 'filename' in entry:
                        dest=P/entry['filename']
                        if not dest.exists():
                            urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode(entry),dest)
if __name__=='__main__':
    (submit if sys.argv[1]=='submit' else status)(sys.argv[2])
