"""Publish only this variant, with preimage checks and recoverable catalog changes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

batch=Path(__file__).resolve().parent
context=json.loads((batch/'locations.json').read_text('utf8'))
art=Path(context['source'])
content=Path(context['project'])/'Content'
stage=batch/'Stage'
host=batch/'Host/Content'
prior=json.loads((batch/'preimages.json').read_text('utf8'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def replace(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as tmp:
        scratch=Path(tmp.name)
        with source.open('rb') as stream:
            shutil.copyfileobj(stream,tmp)
    try:
        os.replace(scratch,target)
    finally:
        scratch.unlink(missing_ok=True)

packages=[]
for receipt in ('authored-head.json','authored-icons.json'):
    packages+=json.loads((batch/receipt).read_text('utf8'))
items={}
for path in packages:
    pkg=path.split('.')[0]
    rel=pkg.removeprefix('/Game/')+'.uasset'
    items[rel]=host/rel
for rel in prior:
    if rel.endswith('.png'):
        items[rel]=art/'Icons'/Path(rel).name
# The catalog switches only after the new mesh, surfaces and UI have been installed.
for name in ('shared-axe-blade-options.json','tactical-hatchet-modules.json'):
    rel='ColdSteelData/'+name
    items[rel]=stage/rel
rows=[]
for rel,src in items.items():
    after=digest(src)
    before=digest(content/rel)
    if not after or before not in (prior.get(rel),after):
        raise RuntimeError('Diverged file '+rel)
    rows.append(dict(file=rel,source=str(src),before=before,sha256=after))
installed=[]
try:
    for row in rows:
        rel=row['file']
        target=content/rel
        if row['before']==row['sha256']:
            continue
        if digest(target)!=row['before']:
            raise RuntimeError('Concurrent change '+rel)
        replace(Path(row['source']),target)
        installed.append(row)
    receipt=dict(revision='SwiftCrescentFactoryFinish20261122',id='axe_swift_crescent',files=rows,
                 inventory_pipeline='ColdSteelWeaponIconCatalog',gameplay_tested=False)
    (batch/'installed.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
except BaseException:
    for row in reversed(installed):
        rel=row['file']
        target=content/rel
        if digest(target)==row['sha256']:
            if row['before'] is None:
                target.unlink()
            else:
                replace(batch/'Before'/rel,target)
    raise
