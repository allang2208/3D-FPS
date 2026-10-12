"""Publish only the two saved overhead animations after the native curve build."""
import hashlib
import json
import re
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonDashArm20261010'
saved=json.loads((out/'assets-saved.json').read_text())
expected={'Melee.FullBody.Overhead','Melee.FullBody.DashOverhead'}
if not saved['complete'] or set(saved['clips'])!=expected:
    raise RuntimeError('Both overhead assets must be saved before publication.')
if saved['source_hash']!=hashlib.sha256((out/'candidate-actions.json').read_bytes()).hexdigest():
    raise RuntimeError('Asset/source revision differs.')
path=root/'Content/ColdSteelData/player_body.json'
text=path.read_text(encoding='utf-8-sig');cfg=json.loads(text)
saved['previous_clips']={k:cfg['clips'][k] for k in expected}
for key,new in saved['clips'].items():
    old=cfg['clips'][key]
    if 'KwangSwordRecovery20261010' not in old:
        raise RuntimeError('The overhead reference changed during authoring: '+key)
    pattern='('+re.escape(json.dumps(key))+r'\s*:\s*)'+re.escape(json.dumps(old))
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(new),text)
    if count!=1:raise RuntimeError('Expected exactly one action reference: '+key)
path.write_text(text,encoding='utf-8')
(out/'assets-published.json').write_text(json.dumps(saved,indent=2))
print('DASH_WRIST_PUBLISHED 2')
