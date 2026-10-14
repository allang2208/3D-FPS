"""Publish the fitted assets after saving and building their native mount code."""
import json
import hashlib
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonSwordGrip20261007'
receipt=json.loads((OUT/'assets-saved.json').read_text())
expected={'Melee.FullBody.'+s for s in ('Uppercut','Overhead','DashOverhead','Whirlwind.Start','Whirlwind.Loop','Whirlwind.End')}
if not receipt.get('complete') or set(receipt['clips'])!=expected:
    raise RuntimeError('All six grip animations must finish saving before publication.')
if receipt.get('source_hash')!=hashlib.sha256((OUT/'adapted-actions.json').read_bytes()).hexdigest():
    raise RuntimeError('The saved assets do not match the current grip authoring output.')
cfgpath=ROOT/'Content/ColdSteelData/player_body.json'
cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
receipt['previous_clips']={key:cfg['clips'].get(key) for key in receipt['clips']}
cfg['clips'].update(receipt['clips'])
cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'assets-published.json').write_text(json.dumps(receipt,indent=2))
print('KWANG_GRIP_PUBLISHED '+str(len(receipt['clips'])))
