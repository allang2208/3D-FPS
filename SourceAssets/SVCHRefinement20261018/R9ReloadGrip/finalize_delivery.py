"""Record saved production outputs independently of prior runtime acceptance."""
import hashlib
import json
from pathlib import Path

O = Path(__file__).parent
P = O.parents[2]
install = json.loads((O / 'install_receipt.json').read_text())
editable = json.loads((O / 'editable_source.json').read_text())
log = (O / 'build-editor.log').read_text(encoding='utf-8-sig', errors='replace')
if not install['saved'] or not editable['saved'] or 'Result: Succeeded' not in log:
    raise RuntimeError('Production outputs still pending')
current = O.parent / 'delivery_receipt.json'
previous = O / 'previous_delivery.json'
if not previous.exists():
    previous.write_bytes(current.read_bytes())
receipt = {
    'revision': 'R9ReloadGrip', 'status': 'Reload profile saved; Editor build succeeded; editable source saved',
    'mesh': install['mesh'], 'mesh_revision': 'R8Surface preserved',
    'profile': install['profile'], 'profile_revision': 'R9ReloadGrip with R7NativeV9 non-reload tracks',
    'profile_sha256': install['profile_sha256'], 'native_skin': install['native_v9_skin'],
    'assets_saved': True, 'saved_asset_count': 1, 'source_animation_assets_modified': False,
    'native_v9_mesh_modified': False, 'right_arm_and_finger_tracks_preserved': True,
    'action_profile_routing': 'SVCH normal/empty reload uses base registration independently of idle/ADS grip',
    'runtime_tested': False, 'visual_acceptance': 'User review pending; no runtime test or new render',
    'editable_source': editable['editable_blend'], 'install_receipt': str(O / 'install_receipt.json'),
    'build': {'target': 'FPSGAMEEditor Win64 Development', 'succeeded': True,
              'log': str(O / 'build-editor.log'),
              'binary_sha256': hashlib.sha256((P / 'Binaries/Win64/UnrealEditor-FPSGAME.dll').read_bytes()).hexdigest()}
}
(O / 'delivery_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
receipt['previous_delivery'] = json.loads(previous.read_text())
current.write_text(json.dumps(receipt, indent=2) + '\n')
print('SVCH_R9_DELIVERY_SAVED')
