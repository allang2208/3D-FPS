"""Install the new, uniquely named revision without replacing loaded V5 packages."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
HOST=ROOT.parent/'PotionWorkbenchDesign20261015/IntegrationV1/UEImportHost'
receipt=json.loads((ROOT/'import-receipt.json').read_text())
if not receipt['complete']:raise RuntimeError('Import incomplete')
records=[]
for package in receipt['saved']:
    if not package.startswith('/Game/Building/PotionWorkbench20261015/ManualV6/'):raise RuntimeError('Unexpected package')
    rel=Path(package.split('.',1)[0].replace('/Game/','',1)+'.uasset');src=HOST/'Content'/rel;dst=PROJECT/'Content'/rel
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:raise RuntimeError('Preserve existing '+str(dst))
    records.append((src,dst,digest))
for src,dst,digest in records:
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copy2(src,dst)
shutil.copy2(ROOT/'AlchemyManualGeometry.h',PROJECT/'Source/FPSGAME/Building/AlchemyManualGeometry.h')
(ROOT/'install-receipt.json').write_text(json.dumps(dict(installed=True,packages=[dict(path=str(d),sha256=h) for s,d,h in records],runtime_tested=False),indent=2),encoding='utf-8')
print('Installed tailored bookmark packages:',len(records))
