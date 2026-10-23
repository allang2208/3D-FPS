"""Publish only this weapon's definitions; preserve concurrent catalog edits."""
import copy
import json
import os
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content/ColdSteelData'
ID = 'ue_runebound_warhammer'
D = '/Game/Weapons/RuneboundWarhammer20261022'

def obj_path(name):
    return D + '/' + name + '.' + name

def append(filename, value):
    path = DATA / filename
    before = path.read_bytes()
    text = before.decode('utf-8-sig')
    data = json.loads(text)
    if ID in data:
        if data[ID] == value:
            return
        raise RuntimeError('Existing definition differs: ' + filename)
    backup = P / 'Before' / filename
    if not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(before)
    end = text.rfind('}')
    entry = json.dumps(ID) + ': ' + json.dumps(value, ensure_ascii=False, indent=2)
    content = text[:end].rstrip() + ',\n  ' + entry.replace('\n', '\n  ') + '\n' + text[end:]
    if path.read_bytes() != before:
        raise RuntimeError('Concurrent catalog write: ' + filename)
    temporary = path.with_name(path.name + '.runebound.tmp')
    temporary.write_text(content, encoding='utf-8', newline='\n')
    os.replace(temporary, path)

item = copy.deepcopy(json.loads((DATA / 'items.json').read_text(encoding='utf-8-sig'))['ue_steel_warhammer'])
item.update(id=ID, name='符文战锤',
    desc='出自北境守誓者的符文战锤，锤首刻纹记录着古老的锻造誓言。长柄适合双手分握，以交错挥击压制近身敌人，蓄势下砸时将力量倾入地面；出手沉重，需为收势留出余地。',
    ue_icon='Icons/' + ID + '.png',
    tool_mesh=obj_path('SM_RuneboundWarhammer'), world_mesh=obj_path('SM_RuneboundWarhammer'),
    modular_melee_catalog='runebound-warhammer-modules.json')
item.pop('rarity', None)
item.pop('grade', None)
append('items.json', item)
formula = copy.deepcopy(json.loads((DATA / 'combat-weapon-formulas.json').read_text(encoding='utf-8-sig'))['ue_steel_warhammer'])
formula['source'] = 'RUNEBOUND_WARHAMMER_STR_CON_20261022'
append('combat-weapon-formulas.json', formula)
(P / 'item_definition.json').write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')

donor = json.loads((DATA / 'warhammer-modules.json').read_text(encoding='utf-8-sig'))
catalog = {
    'version': 1, 'weapon': ID, 'interface': 'runebound_warhammer_integral_v1',
    'arms_mesh': item['tool_viewmodel'], 'root_slot': 'body', 'module_slots': ['body'],
    'drive_bone': 'WPN_root', 'bone_mount': donor['bone_mount'],
    'slots': {'body': {'factory': {'mesh': item['tool_mesh'], 'location_cm': [0, 0, 0],
                                  'appearance': '符文锤首 · 原生长柄 · 完整原装锤体'}}},
}
workbench = {
    'version': 1, 'weapon': ID,
    'traits': [
        {'icon': 'special', 'text': '点按左键施展交错挥击与过顶下砸组成的三连击。'},
        {'icon': 'special', 'text': '按住左键蓄力，蓄满松开砸地并释放冲击波。'},
        {'icon': 'neutral', 'text': '双手持用，支持格挡、冲刺攻击与对应双手钝器武技。'},
    ],
    'columns': [{'key': 'body', 'name': '锤体', 'default': '原装符文战锤',
        'description': '保留原生符文锤首与长柄的完整外形。', 'options': []}],
}
# The modular publication supersedes the initial integral-body recipe.
# Re-running base registration must retain its fitted interfaces and shared libraries.
module_recipe = P / 'ModulesV1/catalog_base.json'
if module_recipe.exists():
    catalog = json.loads(module_recipe.read_text(encoding='utf-8-sig'))
    workbench = json.loads((P / 'ModulesV1/workbench.json').read_text(encoding='utf-8-sig'))
for filename, data in [('runebound-warhammer-modules.json', catalog),
                       ('runebound-warhammer-gunsmith.json', workbench)]:
    path = DATA / filename
    if path.exists() and json.loads(path.read_text(encoding='utf-8-sig')) != data:
        raise RuntimeError('Destination changed: ' + filename)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
shutil.copy2(P / 'Export' / (ID + '.png'), DATA / 'Icons' / (ID + '.png'))
config = ROOT / 'Config/DefaultGame.ini'
before = config.read_bytes()
text = before.decode('utf-8-sig')
line = '+DirectoriesToAlwaysCook=(Path="' + D + '")'
if line not in text:
    # Add within the existing packaging-settings section, alongside the donor.
    anchor = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/SteelWarhammer20261014")'
    if anchor not in text:
        raise RuntimeError('Packaging section anchor unavailable')
    text = text.replace(anchor, anchor + '\n' + line, 1)
    if config.read_bytes() != before:
        raise RuntimeError('Concurrent packaging config write')
    config.write_text(text, encoding='utf-8', newline='\n')
print('Registered ' + ID)
