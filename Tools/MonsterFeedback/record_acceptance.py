"""Collect current monster/UI evidence without treating a completion flag as success."""
import hashlib, json, re
from pathlib import Path
from PIL import Image

root = Path('D:/FPS3D/FPSGAME')
out = root/'SourceAssets/MonsterFeedback20260911'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

tests = {}
for name in ['Maggot-collision-fixed', 'Arena-final', 'HandBrain-fitted',
             'HandBrain-yaw90', 'HandBrain-yaw180', 'Status-final720',
             'Status-forced1080', 'AI-final']:
    report = json.loads((out/(name+'.json')).read_text(encoding='utf-8-sig'))
    assert not report['failed'], (name, report['failed'])
    assert report['passed'], name
    log = (out/(name+'.log')).read_text(encoding='utf-8-sig')
    assert re.search(r'(?:COMPLETE|COMPLETE\w*) failures=0', log), name
    tests[name] = {'passed': len(report['passed']), 'failed': 0,
                   'report': name+'.json', 'log_sha256': digest(out/(name+'.log'))}
    if name.startswith('HandBrain'):
        m = re.search(r'HANDBRAIN_SURFACE min=([-\d.]+) below=(\d+) sampled=(\d+) missing=(\d+)', log)
        assert m and int(m[2]) == 0 and int(m[4]) == 0
        tests[name]['skin_ground'] = dict(min_cm=float(m[1]), underground=int(m[2]),
                                        sampled=int(m[3]), missing=int(m[4]))

log = (out/'Nurse-final.log').read_text(encoding='utf-8-sig')
assert 'NURSE_ACCEPTANCE_COMPLETE failures=0' in log
checks = re.findall(r'NURSE_ASSERT (PASS|FAIL) ([^\r\n]+)', log)
assert checks and all(result == 'PASS' for result, _ in checks)
checks = list(dict.fromkeys(checks))  # The exit request can leave one final repeated timer callback.
(out/'Nurse-final.json').write_text(json.dumps({'passed': [name for _, name in checks],
                                             'failed': [], 'complete': True}, indent=2), encoding='utf-8')
tests['Nurse-final'] = dict(passed=len(checks), failed=0, report='Nurse-final.json', log_sha256=digest(out/'Nurse-final.log'))

images = {}
for name, expected in [('Status-final720', (1280, 720)), ('Status-forced1080', (1920, 1080))]:
    path = out/(name+'.png')
    with Image.open(path) as im:
        assert im.size == expected, (name, im.size, expected)
        images[name] = {'size': list(im.size), 'sha256': digest(path)}
for name in ['HandBrain-before', 'HandBrain-fitted', 'HandBrain-yaw90', 'HandBrain-yaw180']:
    path = out/(name+'.png')
    with Image.open(path) as im:
        images[name] = {'size': list(im.size), 'sha256': digest(path)}

assets = {}
for relative in ['Content/Monsters/HandBrain/SurfaceV07/PA_HandBrain.uasset',
                 'Content/Monsters/HandBrain/SurfaceV07/SK_HandBrain_Surface.uasset',
                 'Content/Monsters/HandBrain/BP_HandBrain.uasset',
                 'Content/ColdSteelData/status_effects.json']:
    path = root/relative
    assets[relative] = {'bytes': path.stat().st_size, 'sha256': digest(path)}

summary = dict(tests=tests, images=images, active_local_assets=assets,
               original_catalog_count=31, live_gameplay_adapters=['poison', 'fear'],
               build='build-9119010.log',
               limits=['Development standalone; no packaged or multiplayer acceptance.',
                       'Generic buff records validate presentation, not additional buff mechanics.',
                       'The initial requested 1080p run autosized to 888x500; retained separately and repeated with ForceRes.',
                       'Binary assets and screenshots remain in the licensed local host.'])
(out/'acceptance-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({name: value['passed'] for name, value in tests.items()}, ensure_ascii=False))
