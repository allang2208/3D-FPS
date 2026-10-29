"""Add the two saved thrust roles with the shared field transaction."""
import json
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
saved=json.loads((OUT/'assets-saved.json').read_text())
if not saved.get('complete'):raise RuntimeError('Save incomplete')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for label,data in saved['bodies'].items():
    section=candidate if label=='jason' else candidate['body_variants'][label]
    for role,asset in data['clips'].items():
        if role in section['clips'] and section['clips'][role]!=asset:raise RuntimeError('Existing role '+role)
        section['clips'][role]=asset
        owned.append(('clips',role) if label=='jason' else ('body_variants',label,'clips',role))
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
receipt=commit(path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(local_configuration=True,roles=saved['bodies'],transaction=receipt,runtime_tested=False,git_commit=None,git_push=None),indent=2,default=str))
print('PISTOL_KUKRI_THRUST_CONNECTED')
