"""Back up only the seven animation/profile destinations owned by this repair."""
from pathlib import Path
import json,hashlib,zipfile
r=Path(__file__).parent;p=r.parents[2];inputs=json.loads((r/'inputs.json').read_text())['hashes']
paths=[k.split('.')[0] for k in inputs if '/SideMagazine20261108/Animations/' in k or '/Profiles/DA_M249_' in k or k.split('.')[0].endswith('/DA_M249_SupportGrip')]
if len(paths)!=7:raise RuntimeError('Expected two actions and five profiles')
if (r/'before.json').exists():raise RuntimeError('Existing baseline retained')
baseline={}
with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
    for path in paths:
        f=p/'Content'/(path.removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(f.read_bytes()).hexdigest()
        if sha!=inputs[path+'.'+path.split('/')[-1]]:raise RuntimeError('Concurrent target change '+path)
        baseline[path]=sha;z.write(f,str(f.relative_to(p)))
(r/'before.json').write_text(json.dumps(baseline,indent=2))
print('M249_SEVEN_REPAIR_DESTINATIONS_BACKED_UP')
