"""Bind the saved cube through the existing shared RSH mount contract."""
import json
import re
from pathlib import Path

O = Path(__file__).resolve().parent
P = O.parents[1]
receipt = json.loads((O / 'import_receipt.json').read_text(encoding='utf8'))
if not receipt.get('complete'):
    raise RuntimeError('Cube model has not finished saving')
path = P / 'Source/FPSGAME/Weapons/RSH12MuzzleAssets.h'
raw = path.read_bytes()
text = raw.decode('utf-8-sig')
mesh_path = receipt['mesh'].split('.')[0]
text = re.sub(r'inline constexpr const TCHAR\* MeshPath = TEXT\("[^"]+"\);',
    f'inline constexpr const TCHAR* MeshPath = TEXT("{mesh_path}");', text)
length = receipt['muzzle_tip_cm'][0]
text = re.sub(r'inline constexpr float LengthCM = [^;]+;',
    f'inline constexpr float LengthCM = {length:.6f}f;', text)
if path.read_bytes() != raw:
    raise RuntimeError('RSH mount header changed during publication')
if text != raw.decode('utf-8-sig'):
    path.write_bytes(text.encode('utf8'))
(O / 'runtime_source_receipt.json').write_text(json.dumps(dict(
    header=str(path), mesh=mesh_path, muzzle_tip_cm=receipt['muzzle_tip_cm'],
    option='rsh12_heavy_suppressor', mount_changed=False, runtime_tested=False), indent=2), encoding='utf8')
print('RSH_CUBE_RUNTIME_SOURCE_SAVED')
