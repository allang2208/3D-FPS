"""Publish this batch after save commandlet and necessary native build succeed."""
import json
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonSwordKwang20261006'
receipt=json.loads((OUT/'assets-saved.json').read_text())
cfgpath=ROOT/'Content/ColdSteelData/player_body.json'
cfg=json.loads(cfgpath.read_text(encoding='utf-8-sig'))
receipt['previous_clips']={key:cfg['clips'].get(key) for key in receipt['clips']}
cfg['clips'].update(receipt['clips'])
cfgpath.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'assets-published.json').write_text(json.dumps(receipt,indent=2))
print('KWANG_SWORD_PUBLISHED '+str(len(receipt['clips'])))
