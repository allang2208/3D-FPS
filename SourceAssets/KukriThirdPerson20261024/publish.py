"""Connect saved Kukri-only roles with the shared configuration transaction."""
import json
import runpy
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
saved=json.loads((OUT/'assets-saved.json').read_text())
if not saved.get('complete'):raise RuntimeError('Finish asset saving before publishing roles')
path=ROOT/'Content/ColdSteelData/player_body.json'
before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'))
for role,asset in saved['clips'].items():candidate['clips'][role]=asset
owned=[('clips',role) for role in saved['clips']]
variants={}
if (OUT/'kaitlin-assets-saved.json').exists():
    female=json.loads((OUT/'kaitlin-assets-saved.json').read_text())
    if not female.get('complete'):raise RuntimeError('Finish native female asset saving before publishing roles')
    for role,asset in female['clips'].items():
        candidate['body_variants']['kaitlin']['clips'][role]=asset
        owned.append(('body_variants','kaitlin','clips',role))
    variants['kaitlin']=female['clips']
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
result=commit(path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(local_configuration=True,clips=saved['clips'],variants=variants,transaction=result,
    git_commit=None,git_push=None,runtime_tested=False),indent=2,default=str))
print('KUKRI_BODY_ROUTES_PUBLISHED '+str(len(saved['clips'])))
