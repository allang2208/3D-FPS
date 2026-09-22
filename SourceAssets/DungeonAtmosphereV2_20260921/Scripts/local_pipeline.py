"""Owned, resumable FLUX.2/TRELLIS.2 jobs. No remote install, restart or queue deletion.

commands: references, fetch-references, meshes, fetch-meshes
An existing receipt is never submitted twice. Failed candidates keep their receipt.
"""
import argparse
import base64
import importlib.util
import json
import subprocess
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE=CFG['endpoint'].rstrip('/')
CLIENT='DungeonAtmosphereV2_20260921'


def request(path,data=None,headers=None):
    body=None if data is None else (data if isinstance(data,bytes) else json.dumps(data).encode())
    return json.load(HTTP.open(urllib.request.Request(BASE+path,body,headers or {'Content-Type':'application/json'}),timeout=25))


def write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def download(item,path):
    if path.exists():
        return
    query=urllib.parse.urlencode({k:item[k] for k in ('filename','subfolder','type') if k in item})
    with HTTP.open(BASE+'/view?'+query,timeout=180) as response:
        path.write_bytes(response.read())


def submit(folder,kind,workflow):
    receipt=folder/(kind+'_receipt.json')
    if receipt.exists():
        print(folder.name,kind,'already submitted',flush=True)
        return
    # Read actual installed node signatures before sending each new workflow.
    for cls in sorted({n['class_type'] for n in workflow.values()}):
        info=request('/object_info/'+cls)
        if cls not in info:
            raise RuntimeError('Required remote node unavailable: '+cls)
        write(ROOT/'Receipts'/('node-'+cls+'.json'),info[cls])
    write(folder/(kind+'_workflow.json'),workflow)
    r=request('/prompt',{'client_id':CLIENT,'prompt':workflow})
    write(receipt,r)
    if 'prompt_id' not in r:
        raise RuntimeError('Submission rejected: '+str(r))
    print(folder.name,kind,r['prompt_id'],flush=True)


def fetch(folder,kind):
    path=folder/(kind+'_receipt.json')
    if not path.exists():
        print(folder.name,kind,'not submitted',flush=True)
        return
    pid=json.loads(path.read_text(encoding='utf-8'))['prompt_id']
    h=request('/history/'+pid).get(pid)
    if not h:
        print(folder.name,kind,'pending',flush=True)
        return
    write(folder/(kind+'_history.json'),h)
    status=h.get('status',{}).get('status_str')
    print(folder.name,kind,status,flush=True)
    if status!='success':
        return
    if kind=='ref':
        for image in h['outputs'].get('14',{}).get('images',[]):
            download(image,folder/'three_views.png')
    else:
        for node,name in [('51','raw.glb'),('53','textured_master.glb')]:
            output=h['outputs'].get(node,{})
            # Export node wrappers use files, meshes or glbs, depending on version.
            items=[v for vv in output.values() if isinstance(vv,list) for v in vv
                   if isinstance(v,dict) and str(v.get('filename','')).lower().endswith('.glb')]
            if not items:
                # This installed exporter writes the GLB but exposes no UI result.
                # Locate the filename only inside this job's owned output directory.
                prefix='raw' if node=='51' else 'textured_master'
                remote='D:/开发文件/ComfyUI/output/'+CLIENT+'/'+folder.name
                ps="Get-ChildItem -LiteralPath '"+remote+"' -Filter '"+prefix+"_*.glb' | Sort-Object LastWriteTime | Select-Object -Last 1 -ExpandProperty Name"
                encoded=base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
                result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','r5080',
                    'powershell','-NoProfile','-EncodedCommand',encoded],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
                filename=result.stdout.strip().lstrip('\ufeff')
                if result.returncode or not filename.lower().endswith('.glb'):
                    raise RuntimeError('Export finished but no GLB found in owned output folder: '+result.stderr[:200])
                items=[{'filename':filename,'subfolder':CLIENT+'/'+folder.name,'type':'output'}]
            download(items[0],folder/name)


def measured_crops(path):
    from PIL import Image
    im=Image.open(path).convert('RGB')
    w,h=im.size
    # Measure nonwhite content separately in each labeled third of this sheet.
    regions=[]
    for i in range(3):
        x0,x1=round(i*w/3),round((i+1)*w/3)
        crop=im.crop((x0,0,x1,h))
        mask=crop.point(lambda x:255 if x<235 else 0).convert('L')
        bbox=mask.getbbox()
        if not bbox:
            raise RuntimeError('Reference view is empty: '+str(i))
        a,b,c,d=bbox
        pad=12
        regions.append({'x':max(x0,x0+a-pad),'y':max(0,b-pad),
                        'width':min(x1,x0+c+pad)-max(x0,x0+a-pad),
                        'height':min(h,d+pad)-max(0,b-pad)})
    return regions


def reference(prop,folder):
    source=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonProps20260920/Scripts/reference.py')
    spec=importlib.util.spec_from_file_location('dungeon_flux',source)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    workflow=module.build_flux2(prop['prompt'],prop['seed'],prefix=CLIENT+'/'+prop['id']+'/three_views')
    submit(folder,'ref',workflow)


def mesh(prop,folder):
    if (folder/'mesh_receipt.json').exists():
        print(prop['id'],'mesh already submitted',flush=True)
        return
    sheet=folder/'three_views.png'
    if not sheet.exists():
        raise RuntimeError('Reference has not been generated: '+str(sheet))
    crops=prop.get('view_crops') or measured_crops(sheet);write(folder/'crops.json',crops)
    boundary=uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{CLIENT}_{prop["id"]}.png"\r\nContent-Type: image/png\r\n\r\n').encode()+sheet.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
    upload=request('/upload/image',body,{'Content-Type':'multipart/form-data; boundary='+boundary})
    write(folder/'upload.json',upload)
    template=Path('D:/FPS3D/FPSGAME/Tools/AssetPipeline/Mechanical3D/workflows/trellis_ss64.api.json')
    w=json.loads(template.read_text(encoding='utf-8'))
    w['10']['inputs']['image']=upload['name']
    for key in ('11','12','20','21','22'):
        w.pop(key,None)
    for i,c in enumerate(crops):
        w[str(110+i)]={'class_type':'ImageCrop','inputs':dict(image=['10',0],**c)}
        w[str(120+i)]={'class_type':'Trellis2PreProcessImage','inputs':{'image':[str(110+i),0], 'padding':24,'remove_background':True,'max_size':2048}}
    w['4']['inputs'].pop('right_image',None)
    w['4']['inputs'].update(seed=prop['seed'],front_image=['120',0],left_image=['121',0],back_image=['122',0])
    if prop.get('use_single_front'):
        w['4']['inputs'].pop('left_image',None);w['4']['inputs'].pop('back_image',None)
    for key,name in [('51','raw'),('53','textured_master')]:
        w[key]['inputs']['filename_prefix']=CLIENT+'/'+prop['id']+'/'+name
    submit(folder,'mesh',w)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['references','fetch-references','meshes','fetch-meshes','status'])
    parser.add_argument('--asset',choices=[p['id'] for p in CFG['props']])
    args=parser.parse_args()
    queue=request('/queue') if args.command=='status' else None
    for p in CFG['props']:
        if args.asset and args.asset!=p['id']:
            continue
        folder=ROOT/'Generated'/p['id']; folder.mkdir(parents=True,exist_ok=True)
        if args.command=='references': reference(p,folder)
        elif args.command=='fetch-references': fetch(folder,'ref')
        elif args.command=='meshes': mesh(p,folder)
        elif args.command=='fetch-meshes': fetch(folder,'mesh')
        else:
            path=folder/'mesh_receipt.json'
            if not path.exists():continue
            pid=json.loads(path.read_text())['prompt_id']
            state=next((key for key,items in queue.items() if isinstance(items,list) and any(isinstance(item,list) and len(item)>1 and item[1]==pid for item in items)),None)
            if state:print(p['id'],state,flush=True)
            else:fetch(folder,'mesh')
