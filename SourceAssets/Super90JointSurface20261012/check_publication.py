"""Verify the formal saved packages match the already-reviewed candidates."""
import json,hashlib
import numpy as np
from geometry import O,load
P=O.parents[1];receipt=json.loads((O/'published.json').read_text());report={'meshes':{},'animations_unchanged':[]}
for key,item in receipt.items():
 a=load(key+'_candidate.json.gz');b=load(key+'_published.json.gz')
 fields=('triangles','weights','uv','normals','materials','bones','skeleton')
 preserved={f:a[f]==b[f] for f in fields}
 delta=float(np.max(np.abs(np.array(a['positions'])-np.array(b['positions']))))
 package=P/'Content'/(item['path'].removeprefix('/Game/')+'.uasset');sha=hashlib.sha256(package.read_bytes()).hexdigest()
 assert all(preserved.values()) and delta<1e-6 and sha==item['saved_sha256'],key
 report['meshes'][key]={'path':item['path'],'matches_reviewed_candidate':True,'max_position_difference_cm':delta,'saved_sha256':sha,**preserved}
for label,item in load('poses.json.gz').items():
 package=P/'Content'/(item['path'].removeprefix('/Game/')+'.uasset')
 assert hashlib.sha256(package.read_bytes()).hexdigest()==item['sha256'],label
 report['animations_unchanged'].append(label)
assert len(report['meshes'])==2
report['passed']=True
(O/'publication_checks.json').write_text(json.dumps(report,indent=2))
print('SUPER90_FORMAL_SAVED_READBACK_PASSED',json.dumps(report))
