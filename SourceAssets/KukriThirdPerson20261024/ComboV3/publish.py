"""Connect exactly this combo's saved roles, preserving shared body config."""
import json,runpy
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
saved=json.loads((OUT/'assets-saved.json').read_text())
if not saved.get('complete'):raise RuntimeError('Finish native asset saving before connecting roles')
path=ROOT/'Content/ColdSteelData/player_body.json';before=path.read_bytes()
candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for body,data in saved['bodies'].items():
    dest=candidate if body=='jason' else candidate['body_variants'][body]
    prefix=() if body=='jason' else ('body_variants',body)
    for role,asset in data['clips'].items():
        dest['clips'][role]=asset;owned.append(prefix+('clips',role))
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
receipt=commit(path,before,candidate,owned_paths=owned,producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(local_configuration=True,roles=saved['bodies'],transaction=receipt,
    runtime_tested=False,git_commit=None,git_push=None),indent=2,default=str))
print('KUKRI_COMBO_ROUTES_CONNECTED')
