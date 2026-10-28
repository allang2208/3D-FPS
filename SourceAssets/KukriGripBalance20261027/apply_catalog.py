"""Apply the approved grip modifiers; do not republish meshes, materials or icons."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
values = {
    'knife_grip_checkered': {'martial_damage_mult': 1.2, 'stamina_mult': 1.1},
    'knife_grip_leather': {'attack_speed_mult': 1.1, 'stamina_mult': .9},
    'knife_grip_laminate': {'heavy_charge_speed_bonus': .2, 'heavy_toughness_mult': 1.2},
}
labels = {'martial_damage_mult': '武技伤害', 'stamina_mult': '攻击体力消耗',
          'attack_speed_mult': '攻击速度', 'heavy_charge_speed_bonus': '重击蓄力速度',
          'heavy_toughness_mult': '重击削韧'}
for relative in ('Content/ColdSteelData/shared-knife-component-options.json',
                 'SourceAssets/KukriComponentVariants20261026/shared-knife-component-options.json'):
    path = ROOT / relative
    original = path.read_bytes()
    catalog = json.loads(original.decode('utf-8-sig'))
    column = next(c for c in catalog['columns'] if c['key'] == 'grip')
    for option in column['options']:
        stats = values.get(option['id'])
        if stats is None:
            continue
        option['stats'] = stats
        option['effects'] = []
        for key, value in stats.items():
            percent = (value if key == 'heavy_charge_speed_bonus' else value - 1) * 100
            benefit = 1 if (percent < 0 if key == 'stamina_mult' else percent > 0) else -1
            option['effects'].append({'text': f'{labels[key]} {percent:+.0f}%', 'benefit': benefit})
    if path.read_bytes() != original:
        raise RuntimeError('Concurrent catalog edit preserved: ' + str(path))
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Saved ' + str(path))
