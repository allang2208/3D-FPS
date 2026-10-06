"""Update only the RSH PSO mounting description after the refit is saved."""
import json
import re
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent
PROJECT = OUTPUT.parents[1]
receipt = json.loads((OUTPUT / 'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete'):
    raise RuntimeError('Refit assets have not finished saving')
path = PROJECT / 'Content/ColdSteelData/gunsmith.json'
before = path.read_text(encoding='utf-8-sig')
decoder = json.JSONDecoder()
position = before.index('[', before.index('"weapons"')) + 1
while True:
    while before[position].isspace() or before[position] == ',':
        position += 1
    weapon, end = decoder.raw_decode(before, position)
    if weapon['id'] == 'ue_rsh12':
        break
    position = end
option = next(item for item in weapon['options']['optic'] if item['id'] == 'pso1_4x')
option['description'] = '经典镜筒与尖点分划，保留原侧挂夹具与锁杆，通过薄连接座安装在 RSH-12 固定枪身侧面。'
indent = re.search(r'[^\S\n]*$', before[:position]).group()
replacement = json.dumps(weapon, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
after = before[:position] + replacement + before[end:]
if path.read_text(encoding='utf-8-sig') != before:
    raise RuntimeError('Catalog changed during RSH publication')
backup = OUTPUT / 'BeforeCatalog/gunsmith.json'
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    backup.write_text(before, encoding='utf8')
path.write_text(after, encoding='utf8')
(OUTPUT / 'catalog_receipt.json').write_text(json.dumps({
    'weapon': 'ue_rsh12', 'option': 'pso1_4x', 'description_only': True,
    'runtime_tested': False,
}, indent=2), encoding='utf8')
print('RSH_REFIT_CATALOG_SAVED pso1_4x')
