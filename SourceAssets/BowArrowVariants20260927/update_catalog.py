"""Author this bow balance revision and three ammo definitions; never edit saves."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
data_dir = ROOT / 'Content/ColdSteelData'
bow_path = data_dir / 'bows.json'
bows = json.loads(bow_path.read_text(encoding='utf-8-sig'))
for bow in bows.values():
    if bow.get('bow_damage_revision', 0) < 1:
        bow['full_damage'] = bow.get('full_damage', 46) * 1.5
        bow['bow_damage_coefficient_scale'] = 1.5
        bow['bow_damage_revision'] = 1
bow_path.write_text(json.dumps(bows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

path = data_dir / 'ammo_types.json'
catalog = json.loads(path.read_text(encoding='utf-8-sig'))
base = '/Game/Weapons/DarkBow20260925/ArrowVariants20260927/'
designs = [
    ('arrow_broadhead', '穿甲箭', 'ArmorPiercing', 1, .2, 0, 0,
     '四棱钢锥配合加固套箍，用于对付披甲目标；与猎箭共用箭杆和弓弦接口。'),
    ('arrow_poison', '淬毒箭', 'Poison', 2, 0., 1, 0,
     '带储毒凹槽的叶形箭镞，深绿绑线便于辨认；命中施加中毒，沿用中毒状态的叠层与消退规则。'),
    ('arrow_serrated', '锯齿箭', 'Serrated', 3, 0., 0, 1,
     '带后向倒齿的宽刃钢镞，暗红绑线标识；命中施加流血，沿用流血状态的叠层与消退规则。'),
]
for id_, name, mesh, order, pen, poison, bleed, description in designs:
    row = next((r for r in catalog['types'] if r['id'] == id_), None)
    if row is None:
        row = {'id': id_}
        catalog['types'].append(row)
    row.update(group='arrow', group_name='箭', name=name, tier_name='蓝阶',
               tier_color='#4C8FD8', description=description,
               icon=f'Icons/ArrowVariants20260927/{id_}.png', order=order,
               enabled=True, allow_infinite_reserve=False, damage_multiplier=1.0,
               physical_armor_penetration=pen, poison_stacks=poison, bleed_stacks=bleed,
               projectile_mesh=base + f'SM_Arrow_{mesh}.SM_Arrow_{mesh}')
wood = next(r for r in catalog['types'] if r['id'] == 'arrow_wood')
wood['projectile_mesh'] = '/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow.SM_Bow_WoodArrow'
wood['icon'] = 'Icons/ArrowVariants20260927/arrow_wood.png'
path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Keep every native fallback in the shared panel/shot path on the same base.
files = [
    'Weapons/Bow/BowWeaponComponent.cpp', 'Weapons/Bow/BowWeaponComponent.h',
    'Weapons/Bow/BowStats.cpp', 'Weapons/Bow/BowGunsmith.cpp',
    'Skills/ColdSteelSkillRules.cpp', 'UI/ColdSteelItemTooltipData.cpp', 'UI/ColdSteelEnhancementWidget.cpp',
]
for relative in files:
    file = ROOT / 'Source/FPSGAME' / relative
    text = file.read_text(encoding='utf-8-sig')
    text = text.replace('TEXT("full_damage"),46', 'TEXT("full_damage"),69')
    text = text.replace('TEXT("full_damage"), 46', 'TEXT("full_damage"), 69')
    text = text.replace('FullDamage = 46.f', 'FullDamage = 69.f')
    text = text.replace('R 搭箭／缓收弓', '短按 R 搭箭／缓收弓，长按 R 切换箭种')
    file.write_text(text, encoding='utf-8')
