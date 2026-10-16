"""Install only the new saved packages, preserving the loaded legacy assets."""
from pathlib import Path
import json, shutil, hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
receipt=json.loads((ROOT/'import-receipt.json').read_text('utf8'))
if receipt['stage']!='assets_saved': raise RuntimeError('Import is incomplete')
records=[]
for asset in receipt['packages']:
    package=asset.split('.')[0]
    if not package.startswith('/Game/Building/PotionWorkbench20261015/ThermometerV9/'):
        raise RuntimeError('Unexpected package '+package)
    relative=Path(package.removeprefix('/Game/')+'.uasset')
    source=ROOT/'UEImportHost/Content'/relative
    target=PROJECT/'Content'/relative
    if target.exists(): raise RuntimeError('New package already exists; do not overwrite a possibly loaded package '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,target)
    records.append({'package':package,'file':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(ROOT/'installed-assets.json').write_text(json.dumps({'stage':'installed','packages':records},indent=2),'utf8')
print('ALCHEMY_THERMOMETER_INSTALLED',len(records))
