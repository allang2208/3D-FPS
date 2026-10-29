"""Replace only Jason/Kaitlin's third-person uppercut role."""
import json
import runpy
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
saved = json.loads((OUT/'assets-saved.json').read_text())
authoring = json.loads((OUT/'authoring.json').read_text())
if not saved.get('complete'):
    raise RuntimeError('Native asset save has not completed')
path = ROOT/'Content/ColdSteelData/player_body.json'
before = path.read_bytes()
candidate = json.loads(before.decode('utf-8-sig'))
owned = []
for label,data in saved['bodies'].items():
    section = candidate if label=='jason' else candidate['body_variants'][label]
    role = 'Kukri.FullBody.Uppercut'
    if section['clips'][role] != authoring['bodies'][label]['previous_uppercut']:
        raise RuntimeError('Active uppercut changed during authoring: '+label)
    section['clips'][role] = data['clips'][role]
    owned.append(('clips',role) if label=='jason' else ('body_variants',label,'clips',role))
commit = runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
transaction = commit(path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(local_configuration=True,roles=saved['bodies'],
    transaction=transaction,runtime_tested=False,git_commit=None,git_push=None),indent=2,default=str))
print('KUKRI_UPPERCUT_ROUTES_CONNECTED')
