"""Publish only the four newly saved dual-combat configuration leaves."""
import json,runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
saved=json.loads((OUT/'assets-saved.json').read_text());source=json.loads((OUT/'authoring.json').read_text())
if not saved.get('complete'):raise RuntimeError('All native assets must be saved before routing')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for label,entry in saved['bodies'].items():
    target=candidate if label=='jason' else candidate['body_variants'][label]
    for role,asset in entry['clips'].items():
        previous=source['bodies'][label]['previous_roles'][role.removeprefix('Kukri.FullBody.')]
        if target['clips'].get(role)!=previous:raise RuntimeError('Role changed during authoring: '+role)
        target['clips'][role]=asset
        owned.append(('clips',role) if label=='jason' else ('body_variants',label,'clips',role))
transaction=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(transaction=transaction,roles=saved['bodies'],runtime_tested=False,git_commit=None,git_push=None),indent=2,default=str))
print('DUAL_FREE3D_V1_ROUTES_CONNECTED')
