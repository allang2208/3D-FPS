"""Apply the user's approved blade-material table; no asset or gameplay tests."""
from pathlib import Path
import json, shutil

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
VALUES = {
    'folded_steel': ({'physical_damage_mult': 1.10, 'stamina_mult': .95},
                     [('物理伤害+10%', 1), ('攻击体力消耗-5%', 1)]),
    'dark_iron': ({'block_stamina_mult': .80, 'toughness_damage_mult': 1.15},
                  [('格挡体力消耗-20%', 1), ('韧性伤害+15%', 1)]),
    'mithril': ({'attack_speed_mult': 1.10, 'stamina_mult': .90, 'physical_damage_mult': .95},
                [('近战攻击速度+10%', 1), ('攻击体力消耗-10%', 1), ('物理伤害-5%', -1)]),
    'damascus_steel': ({'melee_critical_chance_add': 10., 'melee_critical_damage_bonus': .20, 'stamina_mult': 1.10},
                       [('暴击率+10%', 1), ('暴击伤害+20%', 1), ('攻击体力消耗+10%', -1)]),
    'meteoric_iron': ({'physical_damage_mult': 1.15, 'toughness_damage_mult': 1.25, 'attack_speed_mult': .90},
                      [('物理伤害+15%', 1), ('韧性伤害+25%', 1), ('近战攻击速度-10%', -1)]),
}
path = ROOT / 'Content/ColdSteelData/melee-gunsmith.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
backup = P / 'Before/melee-gunsmith.json'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(path, backup)
column = next(c for c in data['columns'] if c['key'] == 'blade_material')
saved = []
for option in column['options']:
    if option['id'] not in VALUES:
        continue
    stats, effects = VALUES[option['id']]
    option['stats'] = stats
    option['effects'] = [{'text': text, 'benefit': benefit} for text, benefit in effects]
    option['special_effects'] = []
    saved.append({'id': option['id'], 'name': option['name'], 'stats': stats})
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
(P / 'catalog-receipt.json').write_text(json.dumps({
    'saved': saved, 'factory_stats': {}, 'scope': 'rune sword melee only', 'gameplay_tested': False
}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('BLADE_MATERIAL_STATS_SAVED', len(saved))
