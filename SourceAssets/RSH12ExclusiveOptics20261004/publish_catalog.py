"""Replace only RSH's two common holographic entries with its exclusive square optics."""
import importlib.util
import json
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
source = O.parent / 'RSH12SquareOpticsBalance20261004/publish_catalog.py'
spec = importlib.util.spec_from_file_location('rsh_square_optics', source)
revision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revision)
path = P / 'Content/ColdSteelData/gunsmith.json'
raw = path.read_bytes()
text = raw.decode('utf-8')
decoder = json.JSONDecoder()
pos = text.index('[', text.index('"weapons"')) + 1
while True:
    while text[pos].isspace() or text[pos] == ',':
        pos += 1
    weapon, end = decoder.raw_decode(text, pos)
    if weapon['id'] == 'ue_rsh12':
        break
    pos = end
before_ids = [o['id'] for o in weapon['options']['optic']]
revision.apply_weapon(weapon)
backup = O / 'Before/gunsmith.json'
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    backup.write_bytes(raw)
line_prefix = text[:pos].rsplit('\n', 1)[-1]
indent = ''.join(c for c in line_prefix if c in ' \t')
replacement = json.dumps(weapon, ensure_ascii=False, indent=2).replace('\n', '\n' + indent)
if path.read_bytes() != raw:
    raise RuntimeError('Catalog changed during RSH exclusive optic publication')
path.write_bytes((text[:pos] + replacement + text[end:]).encode('utf8'))
(O / 'catalog_receipt.json').write_text(json.dumps(dict(
    weapon='ue_rsh12', previous_ids=before_ids,
    current_ids=[o['id'] for o in weapon['options']['optic']],
    exclusive_options=[o for o in weapon['options']['optic'] if o['id'] in (revision.SQUARE, revision.TACTICAL_SQUARE)],
    legacy_id_mapping={'holographic': revision.SQUARE, 'eoth_holographic': revision.TACTICAL_SQUARE},
    migration_scope='UGunsmithSystem::Normalize only for ue_rsh12 / optic; saved items migrate in memory and normal Apply writes the new ID',
    runtime_tested=False,
), ensure_ascii=False, indent=2), encoding='utf8', newline='\n')
print('RSH_EXCLUSIVE_SQUARE_OPTICS_PUBLISHED')
