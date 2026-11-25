"""Create/resume the stablemaster head and clothed body. Credentials stay in process memory."""
import base64,getpass,hashlib,json,os,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image
import requests

PROJECT=Path(__file__).resolve().parents[4]
ROOT=PROJECT/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
REF=ROOT.parent/'StablemasterR2'
API='https://api.meshy.ai/openapi/v1/'
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8');tmp.replace(path)
def read(path):return json.loads(path.read_bytes())
def session():
    s=requests.Session();s.trust_env=False
    s.proxies.update({'https':'http://127.0.0.1:7897','http':'http://127.0.0.1:7897'})
    return s
def prepare(role):
    sheet=Image.open(REF/('FaceTurnaround.png' if role=='Head' else 'RidingHabit.png')).convert('RGB')
    cuts=[0,494,999,1536] if role=='Head' else [100,568,971,1470]
    height=667 if role=='Head' else 1024
    for i in range(3):
        im=sheet.crop((cuts[i],0,cuts[i+1],height))
        path=ROOT/'Inputs'/f'{role}_{i+1}.jpg';path.parent.mkdir(parents=True,exist_ok=True);im.save(path,quality=96,subsampling=0)
def task(key,role,endpoint,params):
    s=session();s.headers['Authorization']='Bearer '+key
    p=ROOT/role;p.mkdir(parents=True,exist_ok=True)
    job=p/'task.json';marker=p/'pending.json'
    if not job.exists():
        if marker.exists():raise RuntimeError('Previous submission needs reconciliation: '+role)
        data=dict(params);request_record=dict(params)
        if endpoint=='multi-image-to-3d':
            imgs=sorted((ROOT/'Inputs').glob(role+'_*.jpg'))
            data['image_urls']=['data:image/jpeg;base64,'+base64.b64encode(a.read_bytes()).decode() for a in imgs]
            request_record['views']=[{'file':a.name,'sha256':hashlib.sha256(a.read_bytes()).hexdigest()} for a in imgs]
        write(marker,request_record)
        resp=s.post(API+endpoint,json=data,timeout=(30,160))
        if resp.status_code!=200 and resp.status_code!=202:
            msg=resp.text.replace(key,'[redacted]')[:380]
            if 400<=resp.status_code<500:marker.unlink()
            raise RuntimeError(f'{role}: Meshy HTTP {resp.status_code}: {msg}')
        write(job,{'id':resp.json()['result'],'endpoint':endpoint,'request':request_record});marker.unlink()
    tid=read(job)['id'];print(role,tid,flush=True)
    while True:
        try:
            resp=s.get(API+endpoint+'/'+tid,timeout=(20,70));resp.raise_for_status();j=resp.json()
        except (requests.Timeout,requests.ConnectionError):
            time.sleep(12);continue
        state={k:j.get(k) for k in ('id','status','progress','consumed_credits','task_error')}
        write(p/'status.json',state)
        if state['status']=='SUCCEEDED':break
        if state['status'] in ('FAILED','CANCELED'):raise RuntimeError(f'{role}: {state}')
        time.sleep(12)
    url=j['result']['rigged_character_glb_url'] if role=='Rig' else j['model_urls']['glb']
    out=p/(role+'.glb')
    if not out.exists():
        for attempt in range(5):
            try:
                with session().get(url,stream=True,timeout=(25,125)) as res:
                    if res.status_code!=200:raise OSError(f'CDN HTTP {res.status_code}')
                    tmp=out.with_suffix('.part')
                    with tmp.open('wb') as file:
                        for chunk in res.iter_content(1024*1024):file.write(chunk)
                    if res.headers.get('Content-Length') and tmp.stat().st_size!=int(res.headers['Content-Length']):raise OSError('short response')
                    tmp.replace(out)
                break
            except (OSError,requests.RequestException):
                if attempt==4:raise RuntimeError('CDN download delayed; rerun to resume '+role) from None
                time.sleep(4)
    print(role,'saved',out.stat().st_size,flush=True);return tid

def main():
    key=os.environ.get('MESHY_API_KEY') or getpass.getpass('Meshy credential: ')
    for role in ('Head','Body'):prepare(role)
    common=dict(ai_model='meshy-7.1',geometry_resolution='2k',texture_model='meshy-7',texture_resolution='4k',enable_pbr=True,should_texture=True,should_remesh=True,topology='triangle',image_enhancement=False,target_formats=['glb'])
    with ThreadPoolExecutor(max_workers=2) as pool:
        head=pool.submit(task,key,'Head','multi-image-to-3d',dict(common,target_polycount=90000))
        body=pool.submit(task,key,'Body','multi-image-to-3d',dict(common,target_polycount=120000,pose_mode='a-pose'))
        tid=body.result()
        task(key,'Rig','rigging',{'input_task_id':tid,'height_meters':1.68})
        head.result()
if __name__=='__main__':main()
