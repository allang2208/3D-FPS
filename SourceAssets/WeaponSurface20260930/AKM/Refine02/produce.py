"""Produce the stronger AKM satin recipe; reuse saved bindings and source maps."""
import json
from pathlib import Path

O = Path(__file__).parent
R01 = O.parent / 'Refine01'
previous = json.loads((R01 / 'apply_receipt.json').read_text())
if not previous.get('complete'):
    raise RuntimeError('Finish the R01 production save first')
source = json.loads((R01 / 'recipe.json').read_text())
centers = {'receiver': .31, 'magazine': .29, 'mount': .44, 'muzzle': .46,
           'optic': .37, 'furniture_metal': .39, 'accessory': .36}
recipe = {'version': 'AKM-AuthoredFinish-Refine02-20261001',
          'previous_version': source['version'], 'root': source['root'],
          'targets': {}, 'masters': previous['masters'],
          'bindings': json.loads((R01 / 'bindings.json').read_text())['meshes'],
          'geometry_changed': False, 'tested': False}
for key, old in source['targets'].items():
    direct = old['direct_override']
    saved = previous['overrides'][old['source']] if direct else previous['instances'][key]
    scalars = {k: v for k, v in old['scalars'].items() if k.startswith('R01_')}
    scalars.update(R01_Roughness=centers[old['role']], R01_SourceRoughnessWeight=.28,
                   R02_SourceColorContrast=.58)
    recipe['targets'][key] = {'path': saved['path'], 'role': old['role'],
        'parent': None if direct else saved['parent'], 'direct_override': direct,
        'scalars': scalars, 'vectors': {'R01_ToneScale': [.58, .60, .64]}}
(O / 'recipe.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
print('AKM_R02_RECIPE_PRODUCED', len(recipe['targets']), 'materials; no asset writes')
