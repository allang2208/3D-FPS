"""Publish only the fitted bipod animation and its shared selector, preserving live inputs."""
from pathlib import Path
import json,hashlib,runpy
r=Path(__file__).resolve().parent;p=r.parents[2]
before=json.loads((r/'before_hashes.json').read_text())
receipt_path=r/'import_receipt.json';owned=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
for rel,sha in before.items():
    package='/Game/'+rel.removeprefix('Content/').removesuffix('.uasset')
    expected=owned.get('asset_hashes',{}).get(package,sha)
    if rel.endswith('.uasset') and hashlib.sha256((p/rel).read_bytes()).hexdigest()!=expected:
        raise RuntimeError('Bipod asset changed during review; preserve it: '+rel)
# The established importer handles the 60/600/200 Hz transition and saves both assets.
(r/'import_receipt.json').write_text(json.dumps(dict(saved_packages=['/Game/Weapons/M249/Bipod/A_M249_Bipod','/Game/Weapons/M249/Bipod/DA_M249_Bipod'],complete=False)))
code=(r.parent/'Repair09/import.py').read_text()
exec(compile(code,str(r/'import.py'),'exec'))
