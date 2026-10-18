import hashlib
import json
from pathlib import Path

task = Path(__file__).parent
project = task.parents[1]
builds = {}
for target in ['Game', 'Editor']:
    receipts = sorted(task.glob(f'Build-*-{target}/result.json'))
    if not receipts:
        raise RuntimeError('Build still pending: ' + target)
    receipt = receipts[-1]
    builds[target] = {
        'receipt': str(receipt.relative_to(project)),
        **json.loads(receipt.read_text(encoding='utf-8-sig')),
    }
sources = [
    'Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyComponent.h',
    'Source/FPSGAME/Characters/FPSPlayerBodyLaser.cpp',
]
report = {
    'scope': 'Suppress remote flashlight emission through the full large-lamb consume state, sharing the existing remote laser gate. Local flashlight suppression was already present.',
    'builds': builds,
    'source_sha256': {p: hashlib.sha256((project / p).read_bytes()).hexdigest() for p in sources},
    'assets_changed': False,
    'live_coding_used': False,
    'game_or_pie_started': False,
    'tested': False,
    'acceptance': 'user testing pending',
}
(task / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('CONSUMABLE_FLASHLIGHT_DELIVERED', list(builds))
