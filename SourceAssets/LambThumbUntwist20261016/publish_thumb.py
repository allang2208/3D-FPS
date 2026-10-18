"""Enable native thumb roll on the large rack only, including its rebuild recipe."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
paths = [
    ('Content/ColdSteelData/potion_use_motion.json', 'roasted_large_lamb'),
    ('SourceAssets/FoodGrip20261003/large_lamb_natural_grasp.json', None),
    ('SourceAssets/LargeLamb20261014/grip_profile.json', None),
]
for relative, family in paths:
    path = ROOT/relative
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    motion = document[family] if family else document
    for field in ('digits', 'right_digits'):
        motion[field]['thumb']['preserve_native_roll'] = True
    note = ' LambThumbUntwist20261016: thumbs retain parent-carried native roll with shortest-arc aim; grip axes, bone lengths and food timing unchanged.'
    if note.strip() not in motion['authoring']:
        motion['authoring'] += note
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Saved', relative)
