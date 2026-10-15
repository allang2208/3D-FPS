"""Publish the saved no-counterweight option into the shared hammer pommel slot."""
import json
import runpy
import shutil
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = ROOT / 'Content/ColdSteelData'
catalog = runpy.run_path(str(P / 'catalog.py'))
option = catalog['OPTION']
receipt = json.loads((P / 'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:
    raise RuntimeError('Save both assets before registering the option')

def write(path, data):
    backup = P / 'Before' / path.relative_to(ROOT)
    if path.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

library = DATA / 'common-hammer-pommels.json'
data = json.loads(library.read_text(encoding='utf-8-sig'))
for index, old in enumerate(data['options']):
    if old['id'] == option['id']:
        # Re-importing appearance must preserve later approved balance edits.
        for key in ('stats', 'effects', 'special_effects'):
            if key in old:
                option[key] = old[key]
        data['options'][index] = option
        break
else:
    data['options'].append(option)
write(library, data)

path = DATA / 'warhammer-modules.json'
data = json.loads(path.read_text(encoding='utf-8-sig'))
row = json.loads((P / 'exports.json').read_text(encoding='utf-8'))['parts'][0]
package = catalog['MESH_DIR'] + '/' + row['mesh']
data['slots']['pommel'][option['id']] = {
    'mesh': package + '.' + row['mesh'],
    'location_cm': row['location_cm'],
    'appearance': option['appearance'],
    'interface': 'warhammer_factory_v1',
    'shared_option_library': library.name,
    'model_revision': 'NoPommelV1'
}
write(path, data)
print('NO_POMMEL_REGISTERED', flush=True)
