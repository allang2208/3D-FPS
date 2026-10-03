"""Publish this gesture's authoring parameters to the shared casting layer."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
pose = json.loads((P/'motion_config.json').read_text(encoding='utf-8'))
guard = json.loads((ROOT/'SourceAssets/RuneSword20260913/FistBraceGuardV20/pose_config.json').read_text(encoding='utf-8'))
pose['fist'] = guard['fist']
pose['source'] = 'LeftHandPowerFist20260923; accepted V21 retains the V20 finger profile'
pose['flex_semantics'] = 'Cumulative segment direction in palm coordinates, not local joint increments'
destination = ROOT/'Content/ColdSteelData/Skills/left_hand_power_fist.json'
destination.write_text(json.dumps(pose, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(destination)
