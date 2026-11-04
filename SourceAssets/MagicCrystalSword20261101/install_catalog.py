"""Publish the magic-crystal naming and the weapon's two exclusive materials."""
from pathlib import Path
import json
import shutil
import runpy

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
DATA = ROOT / 'Content/ColdSteelData'
WEAPON = 'ue_frost_crystal_sword'
PARTS = [
    {'id': 'red_magic_crystal', 'name': '红魔晶', 'tier': 'special', 'weapons': [WEAPON],
     'description': '魔晶双手剑专属。原有晶体纹理染为深红，保留晶面与裂纹的细节。',
     'stats': {'physical_damage_mult': 1.1, 'hit_health_return_ratio': .05},
     'effects': [{'text': '物理伤害+10%', 'benefit': 1}],
     'special_effects': []},
    {'id': 'high_energy_magic_crystal', 'name': '高能魔晶', 'tier': 'special', 'weapons': [WEAPON],
     'description': '魔晶双手剑专属。致密青蓝晶面经过精细抛光，晶纹与内光交错，剑脊饱满，薄刃微透，反光清亮。',
     'stats': {'magic_damage_mult': 1.1, 'hit_mana_return_ratio': .1},
     'effects': [{'text': '魔法伤害+10%', 'benefit': 1}],
     'special_effects': []},
]

def rename(value):
    if isinstance(value, dict): return {k: rename(v) for k, v in value.items()}
    if isinstance(value, list): return [rename(v) for v in value]
    if isinstance(value, str):
        return value.replace('寒晶·双手剑', '魔晶双手剑').replace('寒晶双手剑', '魔晶双手剑').replace('寒晶与苍蓝星辉', '魔晶双手剑与符文长剑').replace('寒晶', '魔晶').replace('魔晶与苍蓝星辉', '魔晶双手剑与符文长剑')
    return value

def publish(filename, transform):
    path = DATA / filename
    before = path.read_bytes()
    data = transform(json.loads(before.decode('utf-8-sig')))
    backup = P / 'BeforeCatalog' / filename
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists(): backup.write_bytes(before)
    if path.read_bytes() != before: raise RuntimeError('Concurrent edit: ' + filename)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return data

def items_update(data):
    data[WEAPON] = rename(data[WEAPON])
    data[WEAPON]['name'] = '魔晶双手剑'
    data[WEAPON]['icon_fallback'] = '魔晶'
    data[WEAPON]['desc'] = ('魔力凝结而成的晶体双手剑。近战攻击附加智力×50%＋精神×50%的魔法伤害，'
        '随本次攻击倍率结算，并受目标魔法防御影响。精神迸发可将这段附伤提升为智力×100%＋精神×100%。'
        '刃部可改造为红魔晶或高能魔晶。')
    return data

items = publish('items.json', items_update)
copy_rules = runpy.run_path(str(ROOT / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))

def melee_update(data):
    data = rename(data)
    column = next(c for c in data['columns'] if c['key'] == 'blade_material')
    ids = {p['id'] for p in PARTS}
    column['options'] = [o for o in column['options'] if o['id'] not in ids]
    for option in column['options']:
        option['weapons'] = [w for w in option.get('weapons', column['weapons']) if w != WEAPON]
    column['options'].extend(PARTS)
    copy_rules['apply_catalog']('melee-gunsmith.json', data, items)
    return data

publish('melee-gunsmith.json', melee_update)
for filename in ['rune-sword-modules.json', 'frost-sword-modules.json', 'shared-sword-pommels.json']:
    publish(filename, rename)

# Both use the approved gray crystal pictogram; quality framing is supplied by UI.
icons = DATA / 'AttachmentIcons20260913'
for part in PARTS:
    shutil.copy2(icons / 'ue_rune_sword_blade_material_frost_crystal.png',
                 icons / (WEAPON + '_blade_material_' + part['id'] + '.png'))
(P / 'catalog-receipt.json').write_text(json.dumps({
    'weapon_id': WEAPON, 'weapon_name': items[WEAPON]['name'],
    'material_options': ['false'] + [p['id'] for p in PARTS],
    'exclusive_quality': 'special', 'rune_sword_magic_crystal_quality': 'legendary',
    'stable_ids_preserved': True}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('MAGIC_CRYSTAL_CATALOG_SAVED')
