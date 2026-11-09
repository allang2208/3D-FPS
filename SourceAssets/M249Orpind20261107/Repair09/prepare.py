"""Own the M249 hand-deployed bipod changes; retain an immutable source baseline."""
from pathlib import Path
import zipfile,json,hashlib
r=Path(__file__).resolve().parent;p=r.parents[2]
paths=['Source/FPSGAME/Weapons/'+n for n in ('WeaponBipodDeploymentComponent.cpp','WeaponBipodDeploymentComponent.h','PKMBipodComponent.cpp','M249Bipod.h')]
with zipfile.ZipFile(r/'before.zip','x',zipfile.ZIP_DEFLATED) as z:
    for rel in paths:z.write(p/rel,rel)
(r/'before_hashes.json').write_text(json.dumps({rel:hashlib.sha256((p/rel).read_bytes()).hexdigest() for rel in paths},indent=2))
for name in ('run.ps1','build.ps1'):
    (r/name).write_text((r.parent/'Repair08'/name).read_text().replace('Repair08','Repair09'),encoding='utf8')
