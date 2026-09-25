"""Acquire the author's public CC0 skin maps and record their provenance."""
import concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3/External/SkinHuman002')
ROOT.mkdir(parents=True,exist_ok=True)
files={'COLOR':'108LHJUJ6pyl4aNmKts87g-seGSWbUUO6','DISP':'1xbv68namYl4PHCsjdg77vFIgFWji7w2l',
       'NRM':'1R6ZojmZaLstnF15PzSfpOFoUk63ciS3S','OCC':'1-ppXKoAN-avbKmfV8dDUgcWDzAFxulFu','SPEC':'1nZb_n3eqJRQ9jakh-I5qsFabfrk6X3X_'}
def fetch(entry):
    kind,fileid=entry;path=ROOT/('Skin_Human_002_'+kind+'.png')
    url='https://drive.usercontent.google.com/download?id='+fileid+'&export=download&confirm=t'
    data=urllib.request.urlopen(url,timeout=60).read()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Not a PNG: '+kind)
    path.write_bytes(data)
    return {'file':path.name,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,files.items()))
license_url='https://3dtextures.me/about/'
(ROOT/'license-page.html').write_bytes(urllib.request.urlopen(license_url,timeout=30).read())
report={'title':'Skin Human 002','author':'Katsukagi / 3DTextures','asset_page':'https://3dtextures.me/2019/01/24/skin-human-002/',
        'license':'CC0','license_page':license_url,'commercial_use':'Explicitly permitted by author FAQ',
        'source_type':'Author-provided PBR skin texture; not asserted to be a photographic scan',
        'note':'File named SPEC is not assumed to be a roughness map; this integration uses authored roughness.',
        'files':rows}
(ROOT/'provenance.json').write_text(json.dumps(report,indent=2))
print('CC0_SKIN_MAPS_ACQUIRED',len(rows))
