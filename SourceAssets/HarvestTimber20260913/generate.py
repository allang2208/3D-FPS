"""One free, local TRELLIS multiview timber mother mesh; never renders or clears queues."""
import json, sys, uuid, urllib.request, urllib.parse
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
BASE = 'http://192.168.3.142:8188'
PREFIX = 'HarvestTimber20260913/seed_913180'

def request(path, data=None, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+path, data, headers or {}), timeout=60))

if sys.argv[1] == 'submit':
    if (ROOT/'receipt.json').exists():
        raise SystemExit('Existing job retained; use fetch.')
    schema = request('/object_info/Trellis2MeshWithVoxelMultiViewGenerator')
    (ROOT/'generator_schema.json').write_text(json.dumps(schema, indent=2))
    params = {}
    for key, spec in schema['Trellis2MeshWithVoxelMultiViewGenerator']['input']['required'].items():
        if len(spec)>1 and 'default' in spec[1]: params[key]=spec[1]['default']
        elif isinstance(spec[0], list): params[key]=spec[0][0]
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="harvest_poplar_three_views.png"\r\nContent-Type: image/png\r\n\r\n').encode()+(ROOT/'three_views.png').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    upload=request('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    (ROOT/'upload.json').write_text(json.dumps(upload,indent=2))
    w=json.loads(Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json').read_text())
    for node in ['11','12','20','21','22']: w.pop(node,None)
    w['10']['inputs']['image']=upload['name']
    width,height=Image.open(ROOT/'three_views.png').size
    # Boundaries lie in this sheet's actual white gutters, not at assumed thirds.
    cuts=[0,570,1072,width]
    for i in range(3):
        left,right=cuts[i:i+2]
        w[str(110+i)]={'class_type':'ImageCrop','inputs':{'image':['10',0],'x':left,'y':0,'width':right-left,'height':height}}
        w[str(120+i)]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[str(110+i),0],'padding':24,'remove_background':True,'max_size':2048}}
        w[str(130+i)]={'class_type':'SaveImage','inputs':{'images':[str(120+i),0],'filename_prefix':PREFIX+'/view'+str(i)}}
    params.update(pipeline=['1',0],front_image=['120',0],right_image=['121',0],back_image=['122',0],seed=913180,
        pipeline_type='1024_cascade',sparse_structure_resolution=64,sparse_structure_steps=16,shape_steps=24,
        texture_steps=20,generate_texture_slat=True,fill_holes=True,keep_only_shell=True)
    w['4']={'class_type':'Trellis2MeshWithVoxelMultiViewGenerator','inputs':params}
    w['52']['inputs'].update(texture_size=2048,target_face_num=80000,resolution=1024)
    w['51']['inputs']['filename_prefix']=PREFIX+'/raw'
    w['53']['inputs']['filename_prefix']=PREFIX+'/textured_master'
    (ROOT/'workflow.json').write_text(json.dumps(w,indent=2))
    receipt=request('/prompt',json.dumps({'client_id':'HarvestTimber20260913','prompt':w}).encode(),{'Content-Type':'application/json'})
    (ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2));print(receipt)
else:
    pid=json.loads((ROOT/'receipt.json').read_text())['prompt_id']
    history=request('/history/'+pid).get(pid)
    if not history:
        queue=request('/queue')
        print({'status':'pending','running':len(queue['queue_running']),'queued':len(queue['queue_pending'])})
        raise SystemExit()
    (ROOT/'history.json').write_text(json.dumps(history,indent=2))
    print(history['status'])
    if history['status']['status_str']=='success':
        # Trellis2ExportMesh saves GLBs without adding a UI entry to history.outputs.
        for filename in ('raw_00001_.glb','textured_master_00001_.glb'):
            dest=ROOT/filename
            if not dest.exists():
                urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode({'filename':filename,'subfolder':PREFIX,'type':'output'}),dest)
        for output in history['outputs'].values():
            for values in output.values():
                if not isinstance(values,list): continue
                for entry in values:
                    if not isinstance(entry,dict) or not entry.get('filename'): continue
                    name=entry['filename']
                    if not name.endswith(('.glb','.png')): continue
                    dest=ROOT/name
                    if not dest.exists(): urllib.request.urlretrieve(BASE+'/view?'+urllib.parse.urlencode(entry),dest)
        print('Downloaded model and conditioning views only; no rendering.')
