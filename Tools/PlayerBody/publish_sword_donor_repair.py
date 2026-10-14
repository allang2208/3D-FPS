"""Publish only the three saved sword actions, preserving other session edits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006'
receipt = json.loads((OUT/'assets-saved.json').read_text())
path = ROOT/'Content/ColdSteelData/player_body.json'
config = json.loads(path.read_text(encoding='utf-8-sig'))
replaced = {k:config['clips'].get(k) for k in receipt['runtime_clips']}
config['clips'].update(receipt['runtime_clips'])
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'published.json').write_text(json.dumps(dict(replaced=replaced,active=receipt['runtime_clips']),indent=2))
print('Published saved UAL2 Uppercut / Overhead / DashOverhead')
