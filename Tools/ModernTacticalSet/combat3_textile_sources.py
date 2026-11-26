"""Acquire the CC0 production PBR sets with their source metadata."""
import urllib.request,json,hashlib,concurrent.futures
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/Sources')
def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90).read()
jobs=[];records={}
for asset in ['stretch_poplin','bi_stretch']:
    root=R/asset;root.mkdir(exist_ok=True)
    api=json.loads(fetch('https://api.polyhaven.com/files/'+asset));info=json.loads(fetch('https://api.polyhaven.com/info/'+asset))
    (root/'files.json').write_text(json.dumps(api,indent=2),encoding='utf-8');(root/'info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    for channel in ['Diffuse','nor_gl','arm','Displacement']:
        meta=api[channel]['2k']['png'];url=meta['url'];file=root/url.rsplit('/',1)[1];jobs.append((asset,channel,url,file,meta))
    records[asset]=dict(page='https://polyhaven.com/a/'+asset,license='CC0',license_url='https://polyhaven.com/license',metadata=info,files={})
def get(job):
    asset,channel,url,file,meta=job
    if not file.exists():file.write_bytes(fetch(url))
    return asset,channel,dict(file=str(file),url=url,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),provider=meta)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for asset,channel,record in pool.map(get,jobs):records[asset]['files'][channel]=record;print('FABRIC_SOURCE',asset,channel,flush=True)
(R/'textiles.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('TS01_R3_FABRIC_SOURCES_COMPLETE',flush=True)
