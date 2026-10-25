"""Publish only the authorized belt's reload bonus and enhancement policy."""
import json
import os
from pathlib import Path
import sys
import uuid

P = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P / 'Tools/BrownLeatherSet'))
import json_entries

path = P / 'Content/ColdSteelData/items.json'
raw = path.read_bytes()
text = raw.decode('utf-8-sig')
key = 'ue_tactical_magazine_belt'
item = json.loads(text)[key]
fields = dict(bonusStats=dict(reloadSpeed=0.025),
              bonusPerEnhance=dict(reloadSpeed=0.005),
              enhancement=dict(maxLevel=15))
for field, values in fields.items():
    item.setdefault(field, {}).update(values)
updated = json_entries.replace(text, [key], item)
if path.read_bytes() != raw:
    raise RuntimeError('Item catalog changed during scoped publication; retry from current file')
temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
temp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8'))
os.replace(temp, path)
receipt = P / 'SourceAssets/TacticalMagazineBelt20261024/ReloadBonus20261025/catalog_receipt.json'
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(json.dumps(dict(saved=True, definition=key, fields=fields,
    maximum_reload_speed_bonus=0.10, gameplay_tested=False), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Saved tactical belt: +2.5%, +0.5 percentage points per level, cap +15')
