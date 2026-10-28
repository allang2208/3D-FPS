from pathlib import Path
import json, re

BATCH = Path(__file__).resolve().parent
ROOT = BATCH.parents[1]
catalog = json.loads((ROOT/'Content/ColdSteelData/bow-gunsmith.json').read_text(encoding='utf-8-sig'))
selected = {}
ids = {'highland_mountain_echo', 'highland_cadence', 'highland_peakwatch_3_6x'}
def walk(value):
    if isinstance(value, dict):
        if value.get('id') in ids:
            selected[value['id']] = value
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)
walk(catalog)
paths = set()
for option in selected.values():
    paths.update(v for v in option.get('visual', {}).values() if isinstance(v, str) and v.startswith('/Game/'))
for header in ['MountainEchoString.h', 'CadenceString.h', 'BowQuickCombatMotion.h']:
    source = (ROOT/'Source/FPSGAME/Weapons/Bow'/header).read_text(encoding='utf-8-sig')
    paths.update(re.findall(r'TEXT\("(/Game/[^"\r\n]+)"\)', source))
packages = [{'path': p, 'exists': (ROOT/'Content'/(p.removeprefix('/Game/').split('.')[0]+'.uasset')).is_file()} for p in sorted(paths)]
cadence = selected['highland_cadence']
scope = selected['highland_peakwatch_3_6x']['visual']
checks = {
    'three_options_present': set(selected) == ids,
    'restricted_to_highland': all(o.get('weapons') == ['bow_woodsteel'] for o in selected.values()),
    'cadence_passive_window_100_percent': cadence['stats'].get('rhythm_window_bonus') == 1.0,
    'old_passive_speed_removed': cadence['stats'].get('draw_speed_bonus', 0) == 0,
    'cadence_description_current': all(s in str(cadence['special_effects']) for s in ['满层+100%', '6秒', '无需命中目标']),
    'scope_range_3_to_6': scope['bow_scope_min_magnification'] == 3 and scope['bow_scope_max_magnification'] == 6,
    'saved_packages_present': all(p['exists'] for p in packages),
    'always_cook': 'DirectoriesToAlwaysCook=(Path="/Game/Weapons/WoodSteelLongbow20261026")' in (ROOT/'Config/DefaultGame.ini').read_text(encoding='utf-8-sig'),
}
report = {'checks': checks, 'packages': packages, 'visual_acceptance': False, 'actual_socket_transport': False}
(BATCH/'delivery-paths.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'checks': checks, 'packages': len(packages)}, ensure_ascii=False))
raise SystemExit(0 if all(checks.values()) else 1)
