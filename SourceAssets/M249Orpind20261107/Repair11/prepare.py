"""Snapshot the two owned action assets and the current production inputs."""
from pathlib import Path
import hashlib,json,shutil,zipfile
r=Path(__file__).resolve().parent;p=r.parents[2];old=r.parent/'Repair10'
receipt=json.loads((old/'import_receipt.json').read_text());before={}
for package,expected in receipt['asset_hashes'].items():
    rel='Content/'+package.removeprefix('/Game/')+'.uasset'
    sha=hashlib.sha256((p/rel).read_bytes()).hexdigest()
    if sha!=expected:raise RuntimeError('Current asset differs from the previous owned save: '+rel)
    before[rel]=sha
if (r/'before.zip').exists():raise RuntimeError('Keep the existing snapshot')
with zipfile.ZipFile(r/'before.zip','w',zipfile.ZIP_DEFLATED) as z:
    for rel in before:z.write(p/rel,rel)
    for name in ('author.py','bipod.json.gz','authoring.json','import_receipt.json'):
        z.write(old/name,'Repair10/'+name)
for name in ('author.py','motion.py','support_pose.py','hold_fit.json','m24_inputs.pkl','m249_inputs.pkl','geometry.pkl'):
    shutil.copy2(old/name,r/name)
(r/'before_hashes.json').write_text(json.dumps(before,indent=2))
print('Prepared Repair11 source and owned asset backup',flush=True)
