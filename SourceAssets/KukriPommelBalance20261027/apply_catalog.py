"""Apply the approved pommel stats to runtime and reimport sources."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALUES = {
    'knife_pommel_steel': {
        'quick_combat_damage_add': .30,
        'quick_combat_toughness_mult': 1.25,
        'quick_combat_knockback_mult': 1.50,
    },
    'knife_pommel_faceted': {'attack_speed_mult': 1.10, 'stamina_mult': .90},
    'knife_pommel_ringed': {'martial_cooldown_mult': .90, 'stamina_mult': .95},
}
LABELS = {
    'quick_combat_damage_add': '快速打击伤害',
    'quick_combat_toughness_mult': '快速打击削韧',
    'quick_combat_knockback_mult': '快速打击击退距离',
    'attack_speed_mult': '攻击速度',
    'stamina_mult': '攻击体力消耗',
    'martial_cooldown_mult': '武技冷却',
}
for relative in ('Content/ColdSteelData/shared-knife-component-options.json',
                 'SourceAssets/KukriComponentVariants20261026/shared-knife-component-options.json'):
    path = ROOT / relative
    original = path.read_bytes()
    catalog = json.loads(original.decode('utf-8-sig'))
    column = next(c for c in catalog['columns'] if c['key'] == 'pommel')
    for option in column['options']:
        stats = VALUES.get(option['id'])
        if stats is None:
            continue
        option['stats'] = stats
        option['effects'] = []
        for key, value in stats.items():
            percent = (value if key == 'quick_combat_damage_add' else value - 1) * 100
            lower = key in ('stamina_mult', 'martial_cooldown_mult')
            benefit = 1 if (percent < 0 if lower else percent > 0) else -1
            option['effects'].append({'text': f'{LABELS[key]}{percent:+.0f}%', 'benefit': benefit})
    if path.read_bytes() != original:
        raise RuntimeError('Concurrent catalog edit preserved: ' + str(path))
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved ' + str(path))
