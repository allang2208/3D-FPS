"""Append the shared cosmetic material, currently available on the rune sword."""
from pathlib import Path
import json, shutil

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
ID = 'meteoric_iron'
DESCRIPTION = '深灰剑面交织银白晶纹，细腻金属光泽随角度变化。'

def update(filename, apply):
    path = ROOT / 'Content/ColdSteelData' / filename
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    backup = P / 'Before' / filename
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(path, backup)
    apply(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

def catalog(data):
    column = next(c for c in data['columns'] if c['key'] == 'blade_material')
    option = next((o for o in column['options'] if o['id'] == ID), None)
    if option is None:
        option = {'id': ID}
        column['options'].append(option)
    option.update(name='陨铁', description=DESCRIPTION, tier='special',
                  weapons=['ue_rune_sword'], stats={}, effects=[], special_effects=[])

def modules(data):
    data['slots']['blade_material'][ID] = {'mode': 5, 'appearance': '交错晶纹 · 银灰晶带 · 细腻金属光泽'}

update('melee-gunsmith.json', catalog)
update('rune-sword-modules.json', modules)
(P / 'catalog-receipt.json').write_text(json.dumps({
    'id': ID, 'slot': 'blade_material', 'tier': 'special',
    'weapons': ['ue_rune_sword'], 'mode': 5, 'stats': {},
    'other_swords': 'unchanged empty placeholders'
}, indent=2) + '\n', encoding='utf8')
print('METEORIC_IRON_CATALOG_SAVED')
