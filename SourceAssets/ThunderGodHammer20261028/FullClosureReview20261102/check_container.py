"""Compare the real UnrealPak IoStore listing with the hammer dependency inventory."""
from pathlib import Path
import csv, json

out = Path(__file__).parent
with (out / 'packaged-containers.csv').open(encoding='utf-8-sig', newline='') as stream:
    files = {row['Filename'].replace('\\', '/') for row in csv.DictReader(stream, skipinitialspace=True)}
dependencies = json.loads((out / 'dependency-preflight.json').read_text(encoding='utf-8'))
checks = []
for asset in dependencies['assets']:
    suffix = '/Content/' + asset['package'].removeprefix('/Game/') + '.uasset'
    checks.append({'package': asset['package'], 'in_iostore': any(name.endswith(suffix) for name in files)})
result = {'passed': all(row['in_iostore'] for row in checks), 'checks': checks,
          'scope': 'actual scoped Development container, including catalog-derived shared motion dependencies'}
(out / 'package-dependencies.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('IoStore packages:', len(checks), 'missing:', [row['package'] for row in checks if not row['in_iostore']])
raise SystemExit(0 if result['passed'] else 1)
