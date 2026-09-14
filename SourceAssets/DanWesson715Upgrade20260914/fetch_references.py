"""Fetch a pinned public animation reference and retain its license."""
import urllib.request,json,hashlib
from pathlib import Path
O=Path(__file__).parent/'Reference';O.mkdir(exist_ok=True)
repo='ZenXChaos/ThirdPersonShooter-AnimationSets';commit='f19adc2ece4cab0f89c9236223abb97d4d2badea'
files=['license.md','README.md']+['RevolverAnims/Revolver'+x+'.fbx' for x in ['AimIdle','ReloadInit','ReloadLoop','ReloadEnd','SearchAmmo']]
receipt={'repo':'https://github.com/'+repo,'commit':commit,'license':'Unlicense','use':'Third-person hand/forearm motion reference; new 715 mechanical tracks and contact adaptation','files':[]}
for path in files:
    url=f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
    data=urllib.request.urlopen(url,timeout=90).read();dest=O/Path(path).name;dest.write_bytes(data)
    receipt['files'].append({'path':str(dest),'source':url,'sha256':hashlib.sha256(data).hexdigest()});print('REFERENCE_SAVED',dest.name,flush=True)
(O/'provenance.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
