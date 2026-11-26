"""Publish only modern tactical balance fields; preserve art, instances and other items."""
import json, os, sys, uuid
from pathlib import Path
P = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(P / 'Tools/BrownLeatherSet'))
import json_entries as entries
TUNING = json.loads(Path(__file__).with_name('combat_stats.json').read_text(encoding='utf-8'))
for name in ('items.json', 'source-combat-items.json'):
    path = P / 'Content/ColdSteelData' / name
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    doc = json.loads(text)
    for item, fields in TUNING.items():
        for key, value in fields.items():
            text = entries.replace(text, [item, key], value) if key in doc[item] else entries.insert(text, [item], key, value)
            doc[item][key] = value
    tmp = path.with_suffix('.modern-stats-' + uuid.uuid4().hex + '.tmp')
    tmp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + text.replace('\n', newline).encode('utf-8'))
    if path.read_bytes() != raw:
        raise RuntimeError('Concurrent catalog edit: ' + str(path))
    os.replace(tmp, path)
    print('Published five modern tactical entries: ' + str(path), flush=True)
