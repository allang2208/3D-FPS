"""Install only this revision's full-body roles through the field transaction."""
from pathlib import Path
import json, sys

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'Tools/PlayerBody'))
from config_transaction import commit

saved=json.loads((P/'saved-assets.json').read_text())
path=ROOT/'Content/ColdSteelData/player_body.json'
before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'));owned=[]
roles={'Sweep':'Melee.FullBody.HighlandBreakSweep','SweepReady':'Melee.FullBody.HighlandBreakSweepReady','RidgeThrust':'Melee.FullBody.HighlandRidgeThrust'}
for kind,prefix in [('Jason',()),('Kaitlin',('body_variants','kaitlin'))]:
    body=cfg if not prefix else cfg['body_variants']['kaitlin']
    baseline=json.loads((ROOT/'Saved/HighlandThirdPersonReview20261106/native-v3'/kind/'mesh.json').read_text(encoding='utf-8-sig'))
    for role,key in roles.items():
        for suffix,grip in [('', 'Standard'),('.Standard','Standard'),('.LongGrip','LongGrip')]:
            target=saved[kind][grip][role];field=key+suffix
            old=body['clips'].get(field)
            allowed=[None,target]
            if field=='Melee.FullBody.HighlandBreakSweep':allowed.append(baseline['clips'][field]['path'])
            if old not in allowed:raise RuntimeError('Role changed during authoring: '+kind+'/'+field)
            body['clips'][field]=target;owned.append(prefix+('clips',field))
receipt=commit(path,before,cfg,owned_paths=owned,producer=str(Path(__file__).resolve()))
(P/'published.json').write_text(json.dumps(dict(status=receipt['status'],roles=[list(p) for p in owned],
                                            assets=saved,git_commit=None,git_push=None),indent=2))
print('HIGHLAND_BODY_ROLES_INSTALLED',len(owned))
