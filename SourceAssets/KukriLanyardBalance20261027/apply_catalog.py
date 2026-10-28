"""Apply the approved lanyard values to the runtime and reimport catalogs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    'knife_lanyard_braid': {'stamina_mult': .90, 'kill_stamina_max_ratio': .10},
    'knife_lanyard_tag': {'critical_chance_add': 10},
    'knife_lanyard_tassel': {'martial_cooldown_mult': .90, 'physical_damage_mult': 1.05},
}
LABELS = {
    'stamina_mult': '攻击体力消耗',
    'critical_chance_add': '暴击率',
    'martial_cooldown_mult': '武技冷却',
    'physical_damage_mult': '物理伤害',
}
for relative in ('Content/ColdSteelData/shared-knife-component-options.json',
                 'SourceAssets/KukriComponentVariants20261026/shared-knife-component-options.json'):
    path = ROOT / relative
    original = path.read_bytes()
    catalog = json.loads(original.decode('utf-8-sig'))
    column = next(c for c in catalog['columns'] if c['key'] == 'lanyard')
    for option in column['options']:
        stats = VALUES.get(option['id'])
        if stats is None:
            continue
        option['stats'] = stats
        option['effects'] = []
        option['special_effects'] = []
        for key, value in stats.items():
            if key == 'kill_stamina_max_ratio':
                option['special_effects'].append(
                    f'击杀恢复｜装备本武器期间，你每击杀一个目标，恢复最大体力的{value * 100:.0f}%；双持时两把武器分别结算。')
                continue
            percent = value if key == 'critical_chance_add' else (value - 1) * 100
            lower = key in ('stamina_mult', 'martial_cooldown_mult')
            benefit = 1 if (percent < 0 if lower else percent > 0) else -1
            option['effects'].append({'text': f'{LABELS[key]}{percent:+.0f}%', 'benefit': benefit})
    if path.read_bytes() != original:
        raise RuntimeError('Concurrent catalog edit preserved: ' + str(path))
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved ' + str(path))
