import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
receipt=json.loads((P/'install-receipt.json').read_text('utf-8'))
before=json.loads((P/'isolated-inputs.json').read_text('utf-8'))['before']
if not receipt.get('complete'):raise RuntimeError('Compression inspection did not finish')
for package,digest in before.items():
    rel=Path(package[6:]).with_suffix('.uasset');target=ROOT/'Content'/rel
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Runtime animation changed during staging: '+package)
for package in before:
    rel=Path(package[6:]).with_suffix('.uasset');source=P/'AssetHost/Content'/rel;target=ROOT/'Content'/rel
    for suffix in ('.uexp','.ubulk','.uptnl'):
        if source.with_suffix(suffix).exists():shutil.copy2(source.with_suffix(suffix),target.with_suffix(suffix))
    shutil.copy2(source,target)
(P/'asset-publication.json').write_text(json.dumps({'published':True,'assets':list(before)},indent=2),encoding='utf-8')
print('CHIXIAO_GRIP_PUBLISHED',len(before))
