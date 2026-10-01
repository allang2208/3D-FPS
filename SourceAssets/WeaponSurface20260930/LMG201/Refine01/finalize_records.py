"""Record successfully saved binding deltas in the current 201 source manifest."""
import json
from pathlib import Path

O = Path(__file__).parent
receipt = json.loads((O / 'apply_receipt.json').read_text())
if not receipt.get('complete'):
    raise RuntimeError('Assets have not finished saving')
project = O.parents[3]
manifest = project / 'SourceAssets/LMG20120260927/Material21/bindings.json'
data = json.loads(manifest.read_text())
changes = {}
for path, row in receipt['meshes'].items():
    # Preserve geometry/animation revision notes and unrelated material slots.
    data['meshes'].setdefault(path, {}).update(row['bindings'])
    changes[path] = row['bindings']
data['current_material_revision'] = receipt['version']
data['current_surface_recipe'] = 'SourceAssets/WeaponSurface20260930/LMG201/Refine01/recipe.json'
manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
(O / 'bindings.json').write_text(json.dumps({'version': receipt['version'],
    'changed_slots': changes, 'geometry_changed': False, 'tested': False}, indent=2), encoding='utf-8')
print('201_R01_SOURCE_BINDINGS_RECORDED', len(changes))
