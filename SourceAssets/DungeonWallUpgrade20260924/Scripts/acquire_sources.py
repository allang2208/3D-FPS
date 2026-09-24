"""Acquire the approved candidate's PBR source data for local material authoring."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Sources/PolyHaven';OUT.mkdir(parents=True,exist_ok=True)
UA={'User-Agent':'FPSGAMEAssetPipeline/1.0 (local material authoring)'}
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=90) as r:return r.read()
index=json.loads(fetch('https://api.polyhaven.com/files/plastered_wall'))
(OUT/'files.json').write_text(json.dumps(index,indent=2),encoding='utf-8')
channels={'Diffuse':'jpg','nor_dx':'png','arm':'png','Displacement':'png'}
def acquire(item):
    channel,fmt=item;meta=index[channel]['4k'][fmt];p=OUT/meta['url'].rsplit('/',1)[1]
    if not p.exists():
        data=fetch(meta['url'])
        if hashlib.md5(data).hexdigest()!=meta['md5']:raise RuntimeError('Incomplete source download '+channel)
        p.write_bytes(data)
    print('ACQUIRED',channel,p.name,p.stat().st_size,flush=True)
    return channel,dict(file=str(p),url=meta['url'],source_md5=meta['md5'],sha256=hashlib.sha256(p.read_bytes()).hexdigest())
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:files=dict(pool.map(acquire,channels.items()))
record={'title':'Plastered Wall','author':'Amal Kumar','url':'https://polyhaven.com/a/plastered_wall',
        'license':'CC0','license_url':'https://polyhaven.com/license','physical_width_cm':200,
        'resolution':4096,'files':files,'downloaded':True,'production_replacement':False}
(OUT/'provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print('WALL_SCAN_ACQUIRED',flush=True)
