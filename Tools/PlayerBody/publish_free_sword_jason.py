"""Publish only the full-body sword clip keys saved by this task."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
receipt = json.loads((ROOT/'SourceAssets/ThirdPersonSwordFree20261005/assets-saved.json').read_text())
path = ROOT/'Content/ColdSteelData/player_body.json'
config = json.loads(path.read_text(encoding='utf-8-sig'))
config['clips'].update(receipt['runtime_clips'])
# User choice (2026-10-06): all three third-person combo stages share Slash1.
# Keep separate role keys so stage transitions and gameplay contact clocks remain.
for role in ('Melee.FullBody.Slash2', 'Melee.FullBody.Thrust'):
    config['clips'][role] = config['clips']['Melee.FullBody.Slash1']
path.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Published', len(receipt['runtime_clips']), 'saved full-body sword clip keys')
