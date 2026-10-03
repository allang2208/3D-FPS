"""Replace only the saved chainmail traversal entry, preserving parallel edits."""
import json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');before=read(R/'before.json')
asset=P/'Content'/(saved['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
if not saved['saved'] or hashlib.sha256(asset.read_bytes()).hexdigest()!=saved['asset_sha256']:
    raise RuntimeError('Saved repair asset unavailable or changed')
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();c=json.loads(raw.decode('utf-8-sig'))
item=c['items']['ue_chainmail_shirt']
if item['rig_meshes']['Traversal'] not in [before['paths']['ue_chainmail_shirt'],saved['asset']]:
    raise RuntimeError('Traversal chainmail was changed concurrently')
item['rig_meshes']['Traversal']=saved['asset']
if path.read_bytes()!=raw:raise RuntimeError('Outfit configuration changed before publication')
if not (R/'configuration-before.json').exists():(R/'configuration-before.json').write_bytes(raw)
path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'published.json').write_text(json.dumps({'item':'ue_chainmail_shirt','profile':'Traversal',
    'asset':saved['asset'],'runtime_tested':False,'refresh':'next game session'},indent=2))
print('TRAVERSAL_CHAINMAIL_PUBLISHED',flush=True)
