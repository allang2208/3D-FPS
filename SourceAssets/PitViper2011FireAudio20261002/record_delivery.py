"""Update production metadata from the completed import receipt only."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
receipt = json.loads((ROOT / 'import_receipt.json').read_text(encoding='utf8'))
recipe = json.loads((ROOT / 'provenance.json').read_text(encoding='utf8'))
suppressed_path = ROOT / 'suppressed_import_receipt.json'
suppressed = json.loads(suppressed_path.read_text(encoding='utf8')) if suppressed_path.exists() else None
original = ROOT.parent / 'PitViper2011Integration20261002'
path = original / 'import_receipt.json'
if path.exists():
    data = json.loads(path.read_text(encoding='utf8'))
    data['audio']['Fire'].update(
        asset=receipt['asset'], source=receipt['source'],
        source_kind='User-provided ' + Path(recipe['input_actual_path']).name + ', locally processed',
        source_sha256=receipt['source_sha256'],
        repair_receipt=str(ROOT / 'import_receipt.json'))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
path = original / 'delivery_receipt.json'
if path.exists():
    data = json.loads(path.read_text(encoding='utf8'))
    data['fire_audio'] = receipt
    if suppressed:data['pistol_shared_suppressed_audio'] = suppressed
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
print('PIT_VIPER_FIRE_DELIVERY_RECORDED', flush=True)
