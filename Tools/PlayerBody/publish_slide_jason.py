"""Merge saved slide entries into the current body library, preserving other work."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
receipt = json.loads((ROOT/'SourceAssets/ThirdPersonSlide20261005/assets-saved.json').read_text(encoding='utf-8'))
path = ROOT/'Content/ColdSteelData/player_body.json'
config = json.loads(path.read_text(encoding='utf-8-sig'))
config['clips'].update(receipt['runtime_clips'])
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SLIDE_CLIPS_PUBLISHED',len(receipt['runtime_clips']))
