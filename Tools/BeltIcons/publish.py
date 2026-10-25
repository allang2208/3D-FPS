"""Publish scoped grid fields and PNGs without touching quiver or wear assets."""
import hashlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/BeltIcons20261025/ArcaneFrontR1'
D = P / 'Content/ColdSteelData'
sys.path.insert(0, str(P / 'Tools/BrownLeatherSet'))
import json_entries
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

policy = read(P / 'Tools/BeltIcons/policy.json')
saved = read(R / 'saved_icons.json')
if not saved.get('completed'):
    raise RuntimeError('Save the three UE icon textures before publishing')
catalog_path = D / 'items.json'
before = catalog_path.read_bytes()
catalog = json.loads(before.decode('utf-8-sig'))
text = before.decode('utf-8-sig')
changes = []
for key, row in policy['items'].items():
    icon = R / key / (key + '.png')
    if sha(icon) != saved['textures'][key]['icon_sha256']:
        raise RuntimeError('Icon changed after UE save: ' + key)
    if catalog[key]['ue_icon'] != row['icon']:
        raise RuntimeError('Catalog icon route changed concurrently: ' + key)
    old_grid = [catalog[key]['grid_w'], catalog[key]['grid_h']]
    for field in ('grid_w', 'grid_h'):
        text = json_entries.replace(text, [key, field], policy[field])
    changes.append({'item': key, 'old_grid': old_grid, 'grid': [policy['grid_w'], policy['grid_h']],
                    'icon_sha256': sha(icon), 'texture': saved['textures'][key]['asset']})
after = (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
if catalog_path.read_bytes() != before:
    raise RuntimeError('Catalog changed during publication; prepare again')
backup = R / 'Before'
backup.mkdir(parents=True, exist_ok=True)
if not (backup / 'items.json').exists():
    (backup / 'items.json').write_bytes(before)
for key, row in policy['items'].items():
    icon = R / key / (key + '.png')
    for target in (D / row['icon'], D / 'Icons' / icon.name):
        old = backup / ('_'.join(target.relative_to(D).parts))
        if target.exists() and not old.exists():
            shutil.copy2(target, old)
        temporary = target.with_name(target.name + '.belt-' + uuid.uuid4().hex + '.tmp')
        shutil.copy2(icon, temporary)
        os.replace(temporary, target)
temporary = catalog_path.with_name(catalog_path.name + '.belt-' + uuid.uuid4().hex + '.tmp')
temporary.write_bytes(after)
if catalog_path.read_bytes() != before:
    raise RuntimeError('Concurrent catalog writer; retain prepared catalog: ' + str(temporary))
os.replace(temporary, catalog_path)
receipt = {'completed': True, 'revision': policy['revision'], 'items': changes,
           'camera_offset': policy['camera_offset'], 'pixels_per_cell': policy['pixels_per_cell'],
           'quiver_modified': False, 'wear_or_pickup_geometry_modified': False,
           'runtime_tested': False, 'multiplayer_tested': False}
(R / 'published.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BELT_ICONS_PUBLISHED', len(changes), 'grid', policy['grid_w'], policy['grid_h'])
