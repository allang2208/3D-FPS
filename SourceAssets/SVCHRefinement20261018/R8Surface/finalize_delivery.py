"""Record production delivery separately from the historical R7 runtime result."""
import json
from pathlib import Path

O = Path(__file__).parent
target = O.parent / 'delivery_receipt.json'
previous = O / 'previous_delivery.json'
if not previous.exists():
    previous.write_bytes(target.read_bytes())
install = json.loads((O / 'install_receipt.json').read_text())
model = json.loads((O / 'model_receipt.json').read_text())
log = O / 'build-editor.log'
log_text = log.read_text(encoding='utf-8-sig', errors='replace') if log.exists() else ''
built = 'Result: Succeeded' in log_text
receipt = {
    'revision': 'R8Surface',
    'status': 'Assets saved and Editor build succeeded' if built else 'Assets saved; Editor build pending',
    'mesh': install['mesh'],
    'profile': '/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip.DA_SVCH_BaseGrip',
    'profile_revision': 'R7NativeV9 preserved',
    'native_skin': install['outfit_profile']['native_bare_skin'],
    'assets_saved': install['complete'],
    'saved_asset_count': len(install['saved']),
    'native_arm_correctives_saved': 18,
    'weapon_triangles': model['triangles'] - 37086,
    'combined_triangles': model['triangles'],
    'animations_modified': False,
    'runtime_tested': False,
    'visual_acceptance': 'User review pending; no R8 gameplay test or preview render requested',
    'build': {'target': 'FPSGAMEEditor Win64 Development', 'succeeded': built,
              'log': str(log)},
    'install_receipt': str(O / 'install_receipt.json'),
    'previous_delivery': json.loads(previous.read_text())
}
target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(O / 'delivery_receipt.json').write_text(json.dumps({k:v for k,v in receipt.items() if k!='previous_delivery'},
                                                  ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(receipt['status'])
