"""Submit/fetch the owned 5080 multiview jobs; no preview or test launch."""
import json,sys,uuid,urllib.request,urllib.parse,struct
from pathlib import Path
P=Path(__file__).parent
BASE='http://192.168.3.142:8188'
def req(path,data=None,headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path,data=data,headers=headers or {}),timeout=60))
designs={'ballast_hardened':915361,'ballast_rune':915367,'ballast_magic_orb':915373}
selected=sys.argv[2:] or list(designs)
for key in selected:
    folder=P/key;folder.mkdir(exist_ok=True);receipt=folder/'receipt.json'
    if sys.argv[1]=='submit':
        if receipt.exists():print(key,'already submitted',flush=True);continue
        source=folder/'three_views.png';raw=source.read_bytes();width,height=struct.unpack('>II',raw[16:24])
        boundary=uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="frost_pommel_{key}_20260915.png"\r\nContent-Type: image/png\r\n\r\n').encode()+raw+f'\r\n--{boundary}--\r\n'.encode()
        upload=req('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
        (folder/'upload.json').write_text(json.dumps(upload,indent=2))
        w=json.loads((P.parents[1]/'Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json').read_text())
        for node in ('Trellis2LoadModel','Trellis2PreProcessImage','Trellis2MeshWithVoxelMultiViewGenerator','Trellis2MeshWithVoxelToTrimesh','Trellis2OvoxelExportToGLB','Trellis2ExportMesh','ImageCrop'):
            target=P/(node+'.json')
            if not target.exists():target.write_text(json.dumps(req('/object_info/'+node),indent=2))
        w['10']['inputs']['image']=upload['name']
        for k in ('11','12','20','21','22'):w.pop(k,None)
        crops=[]
        for i in range(3):
            x=round(width*i/3);right=round(width*(i+1)/3);crop=str(110+i);pre=str(120+i)
            crops.append({'view':('front','left','back')[i],'x':x,'y':0,'width':right-x,'height':height})
            w[crop]={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':x,'y':0,'width':right-x,'height':height}}
            w[pre]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[crop,0],'padding':24,'remove_background':True,'max_size':2048}}
            w[str(130+i)]={'class_type':'SaveImage','inputs':{'images':[pre,0],'filename_prefix':f'FrostSwordPommels5080_20260915/{key}/view{i}'}}
        (folder/'view_mapping.json').write_text(json.dumps({'size':[width,height],'panels':crops,'up':'mounting neck upward','front_axis':'z'},indent=2))
        schema=json.loads((P/'Trellis2MeshWithVoxelMultiViewGenerator.json').read_text(encoding='utf-8-sig'))['Trellis2MeshWithVoxelMultiViewGenerator']['input']['required']
        pp={}
        for k,v in schema.items():
            if len(v)>1 and 'default' in v[1]:pp[k]=v[1]['default']
            elif isinstance(v[0],list):pp[k]=v[0][0]
        pp.update(pipeline=['1',0],front_image=['120',0],left_image=['121',0],back_image=['122',0],seed=designs[key],pipeline_type='1024_cascade' if key=='ballast_hardened' else '512',sparse_structure_resolution=32,sparse_structure_steps=16,shape_steps=32,texture_steps=24,generate_texture_slat=True,fill_holes=False,keep_only_shell=False,verbose=True)
        w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':pp}
        w['52']['inputs']['resolution']=512 if pp['pipeline_type']=='512' else 1024
        for k,name in [('51','raw'),('53','textured_master')]:w[k]['inputs']['filename_prefix']=f'FrostSwordPommels5080_20260915/{key}/{name}'
        (folder/'workflow.json').write_text(json.dumps(w,indent=2))
        reply=req('/prompt',json.dumps({'client_id':'FrostSwordPommels5080_20260915','prompt':w}).encode(),{'Content-Type':'application/json'})
        receipt.write_text(json.dumps(reply,indent=2));print(key,reply,flush=True)
    else:
        if not receipt.exists():continue
        pid=json.loads(receipt.read_text())['prompt_id'];h=req('/history/'+pid).get(pid)
        if not h:print(key,'pending',flush=True);continue
        (folder/'history.json').write_text(json.dumps(h,indent=2));print(key,h['status']['status_str'],flush=True)
        if h['status']['status_str']!='success':
            for kind,msg in h['status']['messages']:
                if kind=='execution_error':print(msg['exception_message'],flush=True)
            continue
        # Trellis2ExportMesh writes GLBs without UI output records.
        workflow=json.loads((folder/'workflow.json').read_text())
        remote_folder=workflow['51']['inputs']['filename_prefix'].rsplit('/',1)[0]
        for name in ('raw_00001_.glb','textured_master_00001_.glb'):
            dest=folder/name
            if not dest.exists():
                url=BASE+'/view?'+urllib.parse.urlencode({'filename':name,'subfolder':remote_folder,'type':'output'})
                urllib.request.urlretrieve(url,dest);print(key,'downloaded',name,flush=True)
        for node,output in h['outputs'].items():
            for values in output.values():
                if not isinstance(values,list):continue
                for item in values:
                    if not isinstance(item,dict) or 'filename' not in item:continue
                    name=item['filename'];dest=folder/name
                    if dest.exists():continue
                    url=BASE+'/view?'+urllib.parse.urlencode({'filename':name,'subfolder':item.get('subfolder',''),'type':item.get('type','output')})
                    urllib.request.urlretrieve(url,dest);print(key,'downloaded',name,flush=True)
