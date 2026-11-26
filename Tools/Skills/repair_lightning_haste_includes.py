"""Restore the original first include after the action-speed integration."""
import json
import re
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME')
BASE=ROOT/'SourceAssets/LightningHaste20261019'
changed=[]
paths=set()
for receipt in BASE.glob('*progress.json'):
    paths.update(json.loads(receipt.read_text(encoding='utf-8')))
for rel in sorted(paths):
    if not rel.endswith('.cpp'):continue
    original=BASE/'source-before'/rel
    if not original.exists():continue
    match=re.search(r'^#include [^\n]+',original.read_text(encoding='utf-8-sig'),re.M)
    if not match:continue
    first=match.group(0)
    path=ROOT/rel
    s=path.read_text(encoding='utf-8-sig')
    if first in s and not s.startswith(first):
        s=first+'\n'+s.replace(first+'\n','',1)
        path.write_text(s,encoding='utf-8')
        changed.append(rel)
(BASE/'include-repair.json').write_text(json.dumps(changed,indent=2),encoding='utf-8')
print('Restored original first include in',len(changed),'files.')
