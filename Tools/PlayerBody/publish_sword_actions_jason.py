"""Publish only the two saved third-person action roles, retaining other edits."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
receipt = json.loads((ROOT/'SourceAssets/ThirdPersonSwordActions20261006/assets-saved.json').read_text())
path = ROOT/'Content/ColdSteelData/player_body.json'
config = json.loads(path.read_text(encoding='utf-8-sig'))
config['clips'].update(receipt['runtime_clips'])
path.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Published saved third-person uppercut and dash overhead assets')
