"""Summarize completed isolated runtime audits; does not modify game saves."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
results = {}
for kind in ('panoramic', 'scope2x', 'lpvo', 'muzzle'):
    for phase in (('write',) if kind == 'muzzle' else ('write', 'reload')):
        run = 'v3' if kind == 'muzzle' else 'v1'
        path = root / f'{kind}-{run}' / f'{phase}.log'
        text = path.read_text(encoding='utf-8', errors='replace')
        matches = re.findall(r'(?:M4_GUNSMITH: COMPLETE|MUZZLE_MIGRATION_COMPLETE) checks=(\d+) failures=(\d+)', text)
        assert len(matches) == 1, f'Missing/duplicate completion: {path}'
        checks, failures = map(int, matches[0])
        assert failures == 0, f'Failed audit: {path}'
        results[f'{kind}-{phase}'] = {'checks': checks, 'failures': failures, 'log': str(path)}
(root / 'acceptance.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('AKM_ATTACHMENTS_ACCEPTANCE_PASS', sum(r['checks'] for r in results.values()), 'checks')
