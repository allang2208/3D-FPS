"""Switch only the six saved melee references; preserve unrelated configuration."""
import hashlib
import json
import re
from pathlib import Path

root = Path('D:/FPS3D/FPSGAME')
out = root/'SourceAssets/ThirdPersonMeleeRegression20261010'
saved = json.loads((out/'assets-saved.json').read_text())
if not saved['complete'] or len(saved['clips']) != 6:
    raise RuntimeError('Six completed recovery animations are required.')
if saved['source_hash'] != hashlib.sha256((out/'adapted-actions.json').read_bytes()).hexdigest():
    raise RuntimeError('Saved recovery assets have a different authoring source.')
before = json.loads((out/'asset-and-session-before.json').read_text())
path = root/'Content/ColdSteelData/player_body.json'
text = path.read_text(encoding='utf-8-sig')
current = json.loads(text)
saved['previous_clips'] = {k:current['clips'][k] for k in saved['clips']}
for key,new in saved['clips'].items():
    old = before['clips'][key.removeprefix('Melee.FullBody.')]['asset']
    if current['clips'][key] != old:
        raise RuntimeError('Melee configuration changed during authoring: '+key)
    pattern = '('+re.escape(json.dumps(key))+r'\s*:\s*)'+re.escape(json.dumps(old))
    text,count = re.subn(pattern,lambda m:m[1]+json.dumps(new),text)
    if count != 1: raise RuntimeError('Expected one configured action: '+key)
path.write_text(text,encoding='utf-8')
(out/'assets-published.json').write_text(json.dumps(saved,indent=2))
print('KWANG_RECOVERY_PUBLISHED 6')
