"""Collect this audit's receipts without hiding failed attempts."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]

def read(path):
    return json.loads(path.read_bytes())

def native_detail(row):
    directory = Path(row['directory'])
    reports = [p for p in directory.glob('*.json') if p.name in {
        'result.json', 'native-checks.json', 'ballistic-audit.json',
        'camera-audit.json', 'control-audit.json', 'landing-audit.json'}]
    result = dict(row)
    result['passed'] = row['exit_code'] == 0
    for path in reports:
        data = read(path)
        arrays = [v for k, v in data.items() if k in ('checks', 'cases', 'results') and isinstance(v, list)]
        result['check_count'] = sum(len(v) for v in arrays)
        result['failures'] = data.get('failures', data.get('failed', 0))
        result['passed'] &= result['failures'] == 0
        result['report'] = str(path)
    if not reports and (directory/'report.txt').exists():
        text = (directory/'report.txt').read_text(encoding='utf-8-sig')
        match = re.search(r'RESULT checks=(\d+) failures=(\d+)', text)
        if match:
            result['check_count'], result['failures'] = map(int, match.groups())
            result['passed'] &= result['failures'] == 0
        result['report'] = str(directory/'report.txt')
    return result

native_attempts, latest_native = [], {}
for path in sorted((ROOT/'Native').glob('*/receipt.json')):
    rows = read(path)
    for row in rows if isinstance(rows, list) else [rows]:
        item = native_detail(row)
        native_attempts.append(item)
        latest_native[item['name']] = item

wire_attempts, latest_wire = [], {}
for path in sorted((ROOT/'Wire').glob('*/receipt.json'), key=lambda p: p.stat().st_mtime_ns):
    item = read(path)
    item['receipt'] = str(path)
    for side in ('host', 'client'):
        peer = path.parent/(side+'.json')
        if peer.exists():
            item[side] = read(peer)
    wire_attempts.append(item)
    latest_wire[item['case']+'-'+item['mode']] = item

builds = [read(p) for p in sorted((ROOT/'BuildDelivery').glob('build-*.json'))]
files = [p.relative_to(ROOT/'Before').as_posix() for p in (ROOT/'Before').rglob('*') if p.is_file()]
files += ['Source/FPSGAME/Skills/ChainSlashMotion.h', 'Source/FPSGAME/Skills/SessionSkillsAudit20261110.cpp',
          'Source/FPSGAME/Skills/SessionChainWire20261110.cpp']
hashes = {name: hashlib.sha256((PROJECT/name).read_bytes()).hexdigest() for name in files if (PROJECT/name).exists()}
output = {
    'scope': 'Conversation skills audit: source and saved asset review, isolated authority/native simulations and explicitly listed UDP cases.',
    'reviewed_features': ['chainSlash', 'warhammerQuickMelee', 'leapStrike',
                          'flameArmorWeaponAttachments', 'starMarrowCharge',
                          'elementalFireArrow', 'elementalColdArrow', 'magicArrowRainAudio'],
    'changes': [
        'Publish four ChainSlash body phases with the executor acceleration and hitstop clock.',
        'Reject wrong-weapon guard requests before consuming the current guard serial; reject guard during ChainSlash.',
        'Solve standard LeapStrike flight at 0.75s; extend deep drops under gravity and keep actual landing authoritative.',
        'Update both LeapStrike data and detailed panel copy to describe the hybrid flight.',
        'Compare ArrowRain audio with the accepted ordinary-bow donor, replacing the rejected MP3 duration expectation.',
        'Correct frozen-wire fixture equipment/camera/collision setup and advance guard diagnostic time through the existing raise/lower cooldown.'
    ],
    'rendered_or_listened': False,
    'public_internet_or_reconnect_tested': False,
    'leap_udp_movement_tested': False,
    'verification_summary': {
        'native_groups': len(latest_native),
        'native_checks': sum(row.get('check_count', 0) for row in latest_native.values()),
        'latest_native_passed': bool(latest_native) and all(row['passed'] for row in latest_native.values()),
        'udp_cases': len(latest_wire),
        'latest_udp_passed': bool(latest_wire) and all(row['passed'] for row in latest_wire.values()),
    },
    'hammer_previous_animation_backup': read(ROOT/'quick-backup-check.json'),
    'builds': builds,
    'latest_native': latest_native,
    'latest_wire': latest_wire,
    'native_attempts': native_attempts,
    'wire_attempts': wire_attempts,
    'source_sha256_at_collection': hashes,
}
(ROOT/'audit-report.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'native': {k: v['passed'] for k, v in latest_native.items()},
                  'wire': {k: v['passed'] for k, v in latest_wire.items()},
                  'builds': [(b['target'], b['exit_code']) for b in builds]}, ensure_ascii=False))
