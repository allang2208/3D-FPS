"""Render production belt icons from saved scenes with the arcane camera."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/BeltIcons20261025/ArcaneFrontR1'
policy = json.loads((P / 'Tools/BeltIcons/policy.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(P / 'Tools/WorkwearSet'))
from workwear_inventory import studio

chosen = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else list(policy['items'])
for key in chosen:
    row = policy['items'][key]
    source = Path(row['scene'])
    bpy.ops.wm.open_mainfile(filepath=str(source))
    obj = bpy.data.objects[row['object']]
    output = R / key
    renderer = studio(output, key)
    renderer.FAMILIES[key] = row['family']
    result = renderer.render_current(key, obj,
                                    item={name: policy[name] for name in ['grid_w', 'grid_h']},
                                    camera_offset=tuple(policy['camera_offset']))
    receipt = dict(item=key, revision=policy['revision'], source=str(source),
                   source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   grid=[policy['grid_w'], policy['grid_h']], camera_offset=policy['camera_offset'],
                   production=result, runtime_tested=False)
    (output / 'rendered.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('BELT_ICON_RENDERED', key, flush=True)
