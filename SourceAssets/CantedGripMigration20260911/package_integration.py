"""Record this task's delta without staging the host's concurrent AKM work."""
from pathlib import Path
import difflib
import hashlib
import json

O = Path(__file__).resolve().parent
P = O.parents[1]
D = O / 'Integration'
D.mkdir(exist_ok=True)
patches, manifest = [], []
for baseline in sorted((O / 'Baseline').rglob('*')):
    if not baseline.is_file() or baseline.name == 'hashes.json':
        continue
    rel = baseline.relative_to(O / 'Baseline').as_posix()
    before = baseline.read_text(encoding='utf-8-sig')
    live = (P / rel).read_text(encoding='utf-8-sig')
    after = live
    if rel == 'Source/FPSGAME/FPSGAMECharacter.cpp':
        after = before.replace('PrismHandstop.Get(),AngledForegrip.Get()}', 'PrismHandstop.Get(),AngledForegrip.Get(),VerticalForegrip.Get(),CantedForegrip.Get()}')
        after = after.replace('PrismHandstop=nullptr;AngledForegrip=nullptr;', 'PrismHandstop=nullptr;AngledForegrip=nullptr;VerticalForegrip=nullptr;CantedForegrip=nullptr;')
        assert 'VerticalForegrip.Get(),CantedForegrip.Get()}' in live
    if rel == 'Config/DefaultGame.ini':
        anchor = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M4CantedThumbClose")\n'
        additions = '+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M4CantedErgonomic")\n+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M4VerticalGripErgonomic")\n'
        assert anchor in before and additions in live
        after = before.replace(anchor, anchor + additions)
    if before == after:
        continue
    # Export only the reviewed delta. These are records for the complete local host,
    # not an automatically applicable substitute for unpublished AKM prerequisites.
    lines = difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + rel, tofile='b/' + rel, n=0)
    delta = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)
    patches.append('diff --git a/' + rel + ' b/' + rel + '\n' + delta)
    manifest.append({'path': rel, 'baseline_normalized_sha256': hashlib.sha256(before.encode()).hexdigest(), 'task_result_normalized_sha256': hashlib.sha256(after.encode()).hexdigest(), 'working_file_normalized_sha256': hashlib.sha256(live.encode()).hexdigest()})
(D / 'runtime.patch').write_text(''.join(patches), encoding='utf-8')
(D / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

catalog = json.loads((P / 'Content/ColdSteelData/gunsmith.json').read_text(encoding='utf-8'))
weapons = {w['id']: w for w in catalog['weapons']}
m4, akm = weapons['ue_m4a1'], weapons['ue_akm']
comparisons = []
for slot, options in m4['options'].items():
    target = {x['id']: x for x in akm['options'].get(slot, [])}
    for option in options:
        copy = target[option['id']]
        assert copy.get('stats', {}) == option.get('stats', {})
        assert copy.get('effects', []) == option.get('effects', [])
        comparisons.append({'slot': slot, 'id': option['id'], 'stats': copy.get('stats', {}), 'effects': copy.get('effects', []), 'matched': True})
(O / 'catalog_parity.json').write_text(json.dumps(comparisons, indent=2, ensure_ascii=False), encoding='utf-8')
print('INTEGRATION_DELTA', len(manifest), 'CATALOG_PARITY', len(comparisons))
