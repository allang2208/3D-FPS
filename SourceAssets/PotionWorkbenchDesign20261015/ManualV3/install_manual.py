"""Install only this new revision's saved packages, retaining original spellbook assets."""
from pathlib import Path
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
HOST=ROOT.parent/'IntegrationV1/UEImportHost'
receipt=json.loads((ROOT/'import-receipt.json').read_text())
if not receipt['complete']:raise RuntimeError('Import is incomplete')
records=[]
for asset in receipt['saved']:
    rel=Path(asset.split('.',1)[0].replace('/Game/','',1)+'.uasset')
    src=HOST/'Content'/rel;dst=PROJECT/'Content'/rel
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Preserve existing package '+str(dst))
    records.append((src,dst,digest))
for src,dst,digest in records:
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(src,dst)
(ROOT/'install-receipt.json').write_text(json.dumps(dict(installed=True,packages=[dict(path=str(dst),sha256=digest) for src,dst,digest in records],runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
print('MANUAL_PACKAGES_INSTALLED',len(records))
