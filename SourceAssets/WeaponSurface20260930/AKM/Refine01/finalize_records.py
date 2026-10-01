"""Publish current AKM bindings only after the production save completed."""
import json
from pathlib import Path

O = Path(__file__).parent
receipt = json.loads((O / 'apply_receipt.json').read_text())
if not receipt.get('complete'):
    raise RuntimeError('AKM production save is incomplete')
data = {'version': receipt['version'], 'recipe': str(O / 'recipe.json'),
    'meshes': {p: r['bindings'] for p, r in receipt['meshes'].items()},
    'runtime_override_materials': list(receipt['overrides']),
    'geometry_changed': False, 'tested': False}
(O / 'bindings.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
print('AKM_R01_SOURCE_BINDINGS_RECORDED', len(data['meshes']))
