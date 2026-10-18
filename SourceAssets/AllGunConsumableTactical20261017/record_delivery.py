import hashlib
import json
from pathlib import Path

task = Path(__file__).resolve().parent
project = task.parents[1]
builds = {}
for target in ['Game', 'Editor']:
    receipts = sorted(task.glob(f'Build-*-{target}/result.json'))
    if not receipts:
        raise RuntimeError('Build still pending: ' + target)
    receipt = receipts[-1]
    builds[target] = {'receipt': str(receipt.relative_to(project)), **json.loads(receipt.read_text(encoding='utf-8-sig'))}
sources = [
    'Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyComponent.h',
    'Source/FPSGAME/Characters/FPSPlayerBodyLaser.cpp',
    'Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp',
]
report = {
    'scope': 'All catalog guns: hide laser/flashlight during consumable stow in owner first/third-person and remote third-person. Cover single-food offhand lowering/recovery and create remote flashlights for all equipped gun manifests.',
    'source_coverage': 'coverage.json',
    'builds': builds,
    'source_sha256': {p: hashlib.sha256((project / p).read_bytes()).hexdigest() for p in sources},
    'assets_changed': False,
    'game_or_pie_started': False,
    'tested': False,
    'acceptance': 'user gameplay and multiplayer testing pending',
}
(task / 'delivery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('ALL_GUN_CONSUMABLE_TACTICAL_DELIVERED', list(builds))
