"""Publish only the two owned dual thrust animation routes."""
import json,runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
saved=json.loads((OUT/'assets-saved.json').read_text());source=json.loads((OUT/'inputs.json').read_text())
if not saved.get('complete'):raise RuntimeError('Both native thrust assets must be saved before routing')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for label,entry in saved['bodies'].items():
    target=candidate if label=='jason' else candidate['body_variants'][label]
    for role,asset in entry['clips'].items():
        previous=source[label]['previous_roles'].get(role)
        if target['clips'].get(role) not in (previous,asset):raise RuntimeError('Role changed during authoring: '+label+'/'+role)
        target['clips'][role]=asset
        owned.append(('clips',role) if label=='jason' else ('body_variants',label,'clips',role))
transaction=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(transaction=transaction,roles=saved['bodies'],runtime_tested=False,git_commit=None,git_push=None),indent=2,default=str))
print('KUKRI_THRUST_ROUTES_CONNECTED',len(owned))
