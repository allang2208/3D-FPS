"""Copy an existing AKM fixture to isolated slots for material-route diagnosis."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME').resolve()
O = Path(__file__).parent
name = 'AKMMaterialRoute_' + datetime.now().strftime('%Y%m%d_%H%M%S')
directory = P / 'Saved/SaveGames'
copied = []
for suffix in ('_A', '_B'):
    source = directory / ('ColdSteel_AKMIntegrationAudit_akm-metal-v2' + suffix + '.sav')
    checksum = source.with_suffix('.sha1')
    if not source.exists() or not checksum.exists():
        continue
    digest = hashlib.sha1(source.read_bytes()).hexdigest().upper()
    expected = checksum.read_text(encoding='utf-8-sig').strip().upper()
    if digest != expected:
        continue
    target = directory / ('ColdSteel_' + name + suffix + '.sav')
    if target.exists():
        raise RuntimeError('Isolated destination already exists')
    shutil.copy2(source, target)
    shutil.copy2(checksum, target.with_suffix('.sha1'))
    copied.append({'source': str(source), 'target': str(target), 'sha1': digest})
if not copied:
    raise RuntimeError('No readable AKM fixture available')
(O / 'probe.json').write_text(json.dumps({'profile': name, 'copies': copied}, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_ROUTE_FIXTURE', name, 'copied', len(copied), 'slots; player slots untouched', flush=True)
