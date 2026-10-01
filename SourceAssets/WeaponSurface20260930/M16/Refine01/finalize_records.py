"""Publish source bindings after the actual UE production save completes."""
import json
from pathlib import Path

O = Path(__file__).parent
receipt = json.loads((O / 'apply_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):
    raise RuntimeError('M16 production save is incomplete')
data = {'version': receipt['version'], 'recipe': str(O / 'recipe.json'),
    'meshes': {path: row['bindings'] for path, row in receipt['meshes'].items()},
    'wet_library': receipt['weather']['path'], 'geometry_changed': False, 'tested': False}
for file in (O / 'bindings.json', O.parent / 'current_surface_bindings.json'):
    file.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('M16_R01_SOURCE_BINDINGS_RECORDED', len(data['meshes']), 'meshes',
      sum(len(slots) for slots in data['meshes'].values()), 'slots')
