"""Acquire the CC0 MakeHuman base surface and its reference hand landmarks."""
from pathlib import Path
import urllib.request,json,hashlib
root=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/Donor/BareHands')
root.mkdir(exist_ok=True)
base='https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/'
files={'base.obj':'3dobjs/base.obj','default.mhskel':'rigs/default.mhskel','default_weights.mhw':'rigs/default_weights.mhw'}
manifest={}
for name,relative in files.items():
    target=root/name
    if not target.exists():target.write_bytes(urllib.request.urlopen(base+relative,timeout=60).read())
    manifest[name]={'url':base+relative,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
(root/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('BARE_HAND_SOURCE_SAVED')
