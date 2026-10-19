"""Save the revised production icon and synchronize the ST6 recipe and receipts."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;BASE=O.parent;R=BASE.parents[1]
saved=json.loads((O/'saved.json').read_text())
if not saved.get('completed'):raise RuntimeError('Neck meshes are not saved')
for name in ('import_icon.py','publish.py'):
    file=BASE/name
    exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file)})
published=json.loads((BASE/'published.json').read_text())
assets={}
for name in published['saved_assets']+[published['icon']]:
    path=R/'Content'/(name.split('.')[0].removeprefix('/Game/')+'.uasset')
    assets[str(path.relative_to(R))]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
receipt={'completed':True,'revision':'neck-closure','saved_assets':assets,
         'authoring':json.loads((BASE/'author_receipt.json').read_text()),
         'previous_offline_review':'../offline_review.json (earlier revision only)',
         'new_runtime_or_offline_acceptance_performed':False,'game_tested':False}
(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
(BASE/'delivery.json').write_text(json.dumps(receipt,indent=2))
print('ST6_NECK_CLOSURE_PUBLISHED',flush=True)
