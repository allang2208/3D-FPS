"""Publish the saved PKM material bindings for subsequent authoring imports."""
import json
from pathlib import Path

O = Path(__file__).parent
P = O.parents[3]
receipt = json.loads((O / 'apply_receipt.json').read_text())
if not receipt.get('complete'):
    raise RuntimeError('PKM finish assets have not finished saving')
data = {'version': receipt['version'],
    'recipe': 'SourceAssets/WeaponSurface20260930/PKM/Refine01/recipe.json',
    'rebind_script': 'SourceAssets/WeaponSurface20260930/PKM/Refine01/rebind_current.py',
    'meshes': {p: r['bindings'] for p, r in receipt['meshes'].items()},
    'geometry_changed': False, 'tested': False}
for file in (O / 'bindings.json', P / 'SourceAssets/PKMLowpoly20260922/current_surface_bindings.json'):
    file.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('PKM_R01_SOURCE_BINDINGS_RECORDED', len(data['meshes']))
