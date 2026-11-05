"""Apply the M24 extraction clock's 0.6 s reduction to its two base durations."""
import json
import re
from pathlib import Path

output = Path(__file__).resolve().parent
path = output.parents[1] / 'Content/ColdSteelData/gunsmith.json'
raw = path.read_bytes()
text = raw.decode('utf-8')
start = text.index('"id": "ue_m24"')
begin = text.index('{', text.index('"base":', start))
base, length = json.JSONDecoder().raw_decode(text[begin:])
end = begin + length
before = {'reload_time': 4.7, 'empty_reload_time': 6.366666666666666}
after = {'reload_time': 4.1, 'empty_reload_time': 5.766666666666667}
section = text[begin:end]
for key, expected in before.items():
    if base[key] != expected:
        raise RuntimeError('Concurrent M24 duration change preserved: ' + key)
    section, count = re.subn(
        r'("' + key + r'"\s*:\s*)[0-9.]+',
        lambda match: match[1] + repr(after[key]), section, count=1)
    if count != 1:
        raise RuntimeError('Missing M24 duration: ' + key)
if path.read_bytes() != raw:
    raise RuntimeError('Catalog changed during preparation; no write performed')
path.write_bytes((text[:begin] + section + text[end:]).encode('utf-8'))
(output / 'catalog_receipt.json').write_text(json.dumps({
    'weapon': 'ue_m24', 'before': before, 'after': after,
    'runtime_tested': False,
    'scope': 'Only the two M24 base durations; keep all other catalog text'
}, indent=2), encoding='utf-8')
print('M24_RELOAD_TEMPO_CATALOG_SAVED')
