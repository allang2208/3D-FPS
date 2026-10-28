"""Publish the standard framed masters to the exact keys consumed by the workbench."""
import hashlib, json, shutil
from datetime import datetime
from pathlib import Path
P=Path(__file__).resolve().parent
manifest=json.loads((P/'manifest.json').read_text(encoding='utf-8'))
masters={m['id']:m for m in manifest['masters']}
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),'bindings':[],
         'runtime_tested':False,'numeric_changes':False}
for binding in manifest['bindings']:
    source=Path(masters[binding['master']]['output'])
    if not source.exists():raise RuntimeError('Final master missing: '+str(source))
for binding in manifest['bindings']:
    source=Path(masters[binding['master']]['output']);target=Path(binding['runtime_png'])
    # Preserve the pre-import binary too; only these exact icon packages are owned.
    asset=target.with_suffix('.uasset');backup=P/'Before'/asset.name
    if asset.exists() and not backup.exists():shutil.copy2(asset,backup)
    shutil.copy2(source,target)
    receipt['bindings'].append({**binding,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
receipt['complete']=True
(P/'Receipts/deployment.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"KUKRI_STANDARD_ICONS_DEPLOYED {len(receipt['bindings'])} bindings / {len(masters)} masters")
