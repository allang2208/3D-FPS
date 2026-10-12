"""Publish only the three saved Tang Dao action references."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonTangDaoWhirlwind20261010'
receipt = json.loads((OUT / 'assets-saved.json').read_text())
if not receipt['complete'] or len(receipt['clips']) != 3:
    raise RuntimeError('All three variants must be saved before publishing.')
path = ROOT / 'Content/ColdSteelData/player_body.json'
with path.open('r', encoding='utf-8-sig', newline='') as stream:
    raw = stream.read()
current = json.loads(raw)
previous = {}
for key, value in receipt['clips'].items():
    previous[key] = current['clips'].get(key)
    if previous[key] and previous[key] != value:
        raise RuntimeError('Another revision already owns ' + key)
    package = value.split('.')[0].removeprefix('/Game/')
    if not (ROOT / 'Content' / (package + '.uasset')).is_file():
        raise RuntimeError('Saved package missing for ' + key)
missing = {k: v for k, v in receipt['clips'].items() if k not in current['clips']}
if missing:
    lines = raw.splitlines(keepends=True)
    anchor = next(i for i, line in enumerate(lines) if '"Melee.FullBody.Whirlwind.End":' in line)
    indent = lines[anchor][:len(lines[anchor])-len(lines[anchor].lstrip())]
    ending = '\r\n' if lines[anchor].endswith('\r\n') else '\n'
    lines[anchor+1:anchor+1] = [indent + json.dumps(k) + ': ' + json.dumps(v) + ',' + ending for k, v in missing.items()]
    with path.open('w', encoding='utf-8', newline='') as stream:
        stream.write(''.join(lines))
(OUT / 'assets-published.json').write_text(json.dumps({
    'published': receipt['clips'], 'previous': previous,
    'source_hash': receipt['source_hash'],
    'build_log': 'Saved/BuildEditor/build-20261010-200112.log',
    'runtime_tested': False,
}, indent=2), encoding='utf-8')
print('TANG_DAO_WHIRLWIND_PUBLISHED ' + ', '.join(receipt['clips']))
