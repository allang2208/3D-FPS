"""Apply the user-approved blade modifiers without republishing any art assets."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
values = {
    'swift_blade': dict(physical_damage_mult=.95, attack_speed_mult=1.15, stamina_mult=.85, toughness_damage_mult=.85),
    'heavy_back_blade': dict(physical_damage_mult=1.2, attack_speed_mult=.9, stamina_mult=1.1, toughness_damage_mult=1.25),
    'folded_balanced_blade': dict(physical_damage_mult=1.1, attack_speed_mult=1., stamina_mult=1., toughness_damage_mult=1.1),
}
labels = {'physical_damage_mult': '物理伤害', 'attack_speed_mult': '攻击速度',
          'stamina_mult': '攻击体力消耗', 'toughness_damage_mult': '削韧'}
for relative in ('Content/ColdSteelData/shared-knife-blade-options.json',
                 'SourceAssets/KukriBladeVariants20261026/shared-knife-blade-options.json'):
    path = ROOT / relative
    original = path.read_bytes()
    catalog = json.loads(original.decode('utf-8-sig'))
    for option in catalog['options']:
        stats = values.get(option['id'])
        if stats is None:
            continue
        option['stats'].update(stats)
        option['effects'] = [dict(text=f'{labels[key]} {(value-1)*100:+.0f}%',
                                  benefit=1 if (value < 1 if key == 'stamina_mult' else value > 1) else -1)
                             for key, value in stats.items() if value != 1]
    if path.read_bytes() != original:
        raise RuntimeError('Concurrent catalog edit preserved: ' + str(path))
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Saved ' + str(path))
