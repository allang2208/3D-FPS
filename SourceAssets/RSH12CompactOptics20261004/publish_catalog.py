"""Change only the descriptions of the two RSH optics; retain IDs and stats."""
import json
import re
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
receipt = json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete'):
    raise RuntimeError('Compact optic assets have not finished saving')
path = P/'Content/ColdSteelData/gunsmith.json'
before = path.read_text(encoding='utf-8-sig')
decoder = json.JSONDecoder()
position = before.index('[', before.index('"weapons"'))+1
while True:
    while before[position].isspace() or before[position] == ',':
        position += 1
    weapon, end = decoder.raw_decode(before, position)
    if weapon['id'] == 'ue_rsh12':
        break
    position = end
descriptions = {
    'holographic': 'RSH-12 紧凑适配型，开放式短镜框与低位夹座贴合上导轨，保留 1× 环点分划。',
    'eoth_holographic': 'RSH-12 紧凑适配型，短保护罩、独立透光镜片与环点分划，低位夹座直接安装在上导轨。',
}
for option in weapon['options']['optic']:
    if option['id'] in descriptions:
        option['description'] = descriptions[option['id']]
# Retain the accepted square-sight names and tuning on subsequent optic imports.
revision = O.parent/'RSH12SquareOpticsBalance20261004/publish_catalog.py'
if revision.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location('rsh_square_optics_revision', revision)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.apply_weapon(weapon)
indent = re.search(r'[^\S\n]*$', before[:position]).group()
replacement = json.dumps(weapon, ensure_ascii=False, indent=2).replace('\n', '\n'+indent)
after = before[:position]+replacement+before[end:]
if path.read_text(encoding='utf-8-sig') != before:
    raise RuntimeError('Catalog changed during compact optic publication')
backup = O/'BeforeCatalog/gunsmith.json'
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    backup.write_text(before, encoding='utf8')
path.write_text(after, encoding='utf8')
(O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12', options=[o['id'] for o in weapon['options']['optic']],
    descriptions_only=not revision.exists(), square_optic_revision_applied=revision.exists(),
    shared_icons_preserved=True, runtime_tested=False), indent=2), encoding='utf8')
print('RSH_COMPACT_OPTIC_CATALOG_SAVED')
