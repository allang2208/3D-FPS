"""Append wildlife harvest items to items.json without reformatting the file."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'Content/ColdSteelData/items.json'

MEAT = [
    ('raw_venison', '生鹿肉', '带血的新鲜鹿肉，需在篝火烤熟后食用。'),
    ('raw_boar_meat', '生野猪肉', '纹理粗糙的野猪肉，油脂厚，需烤熟后食用。'),
    ('raw_fox_meat', '生狐肉', '气味浓烈的狐肉，需烤熟后食用。'),
]
HIDE = [
    ('deer_hide', '鹿皮', '柔韧的鹿皮，可作皮革工艺的原料。'),
    ('boar_hide', '野猪皮', '厚实耐磨的野猪皮，适合做护具与包具的衬底。'),
    ('fox_pelt', '狐皮', '蓬松的狐皮，冬季毛色最完整。'),
    ('wolf_pelt', '狼皮', '成年野狼的完整毛皮，脊背处留有旧伤痕。'),
    ('crow_feather', '鸦羽', '漆黑的飞羽，常被用作箭羽与装饰。'),
    ('deer_antler', '鹿角', '公鹿脱落的角，可打磨成工具柄与饰件。'),
    ('boar_tusk', '野猪獠牙', '弯曲的獠牙，尖端仍带磨损。'),
]

entries = {}
for item_id, name, desc in MEAT:
    entries[item_id] = {
        'id': item_id, 'name': name, 'category': 'material', 'type': '食材',
        'rarity': 'common', 'level': 1,
        'grid_w': 1, 'grid_h': 1, 'stack': 1, 'stack_max': 1, 'maxStack': 1,
        'spoilDays': 3,
        'desc': desc + '野生动物身上取得，尚未有对应的烹饪配方。',
        'icon': '', 'icon_fallback': name,
        'world_mesh': '',
        'artPending': 'icon and world mesh not produced yet; loot goes straight to the bag',
    }
for item_id, name, desc in HIDE:
    entries[item_id] = {
        'id': item_id, 'name': name, 'category': 'material', 'type': '材料',
        'rarity': 'common', 'level': 1,
        'grid_w': 1, 'grid_h': 1, 'stack': 20, 'stack_max': 20, 'maxStack': 20,
        'desc': desc,
        'icon': '', 'icon_fallback': name,
        'world_mesh': '/Game/Monsters/Wildlife/Trophies/SM_' + item_id + '.SM_' + item_id,
        'artPending': 'inventory icon',
    }

raw = PATH.read_text(encoding='utf-8')
data = json.loads(raw)
added = [key for key in entries if key not in data]
if not added:
    print('Wildlife loot definitions already exist')
    raise SystemExit(0)
for key in added:
    data[key] = entries[key]

blocks = []
for key in added:
    body = json.dumps(entries[key], ensure_ascii=False, indent=2)
    body = '\n'.join('  ' + line for line in body.splitlines())
    blocks.append('  "' + key + '": ' + body.lstrip())

tail = raw.rstrip()
assert tail.endswith('}'), 'unexpected items.json tail'
head = tail[:-1].rstrip()
if not head.endswith(','):
    head += ','
merged = head + '\n' + ',\n'.join(blocks) + '\n}\n'
json.loads(merged)  # fail fast instead of writing a broken catalog
PATH.write_text(merged, encoding='utf-8', newline='\n')
print('WILDLIFE_ITEMS_ADDED', len(added), added)
