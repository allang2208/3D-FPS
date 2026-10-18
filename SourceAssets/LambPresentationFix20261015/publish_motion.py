"""Publish only the two authored lamb motion families, retaining live clocks."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
apply_motion = runpy.run_path(str(ROOT/'SourceAssets/FoodGrip20261003/lamb_food_motion.py'))['apply_lamb_motion']
path = ROOT/'Content/ColdSteelData/potion_use_motion.json'
original = path.read_bytes()
data = json.loads(original.decode('utf-8-sig'))
for item, folder, large in [('roasted_lamb_ribs', 'LambRibs20261014', False),
                           ('roasted_large_lamb', 'LargeLamb20261014', True)]:
    profile_path = ROOT/'SourceAssets'/folder/'grip_profile.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    profile['times'] = data[item]['times']
    data[item] = apply_motion(profile, large)
    profile_path.write_text(json.dumps(data[item], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert path.read_bytes() == original, 'Concurrent motion edit; publish again from the current file.'
path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Published the two lamb families; live action clocks retained.')
