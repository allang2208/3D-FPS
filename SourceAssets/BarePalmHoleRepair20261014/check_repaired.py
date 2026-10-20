import json,numpy as np
from pathlib import Path
from analyze_surface import analyze
from plan_repair import palm_weight
R=Path(__file__).resolve().parent
plans={v['path']:v for v in json.loads((R/'repair_plan.json').read_text())};rows=[]
for file in (R/'After').glob('*.json'):
 d=json.loads(file.read_text());r=analyze(d);entry=plans[d['path']]
 v=np.array(d['positions']);t=np.array(d['triangles']);n=np.array(d['normals'])
 sign=np.einsum('ij,ij->i',np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]),n.mean(1));orientation=np.sign(np.median(sign))
 patch_t=[]
 for patch in entry['patches']:
  centers=set(np.where(np.linalg.norm(v-np.array(patch['center']),axis=1)<.0001)[0].tolist())
  patch_t += [i for i,tri in enumerate(t) if any(vi in centers for vi in tri)]
 holes=[c for c in r['boundary_components'] if max(c['span'])<.5 and np.mean([palm_weight(d['weights'][i]) for i in c['vertices']])>.65]
 bad=[i for i in patch_t if sign[i]*orientation < -1e-8]
 row=dict(path=d['path'],small_palm_openings=len(holes),new_patch_triangles=len(patch_t),new_patch_flips=bad,seam_weight_splits=len(r['seam_weight_splits']))
 rows.append(row);print(d['path'],'openings',len(holes),'new flipped',len(bad),'weight splits',len(r['seam_weight_splits']))
(R/'readback_findings.json').write_text(json.dumps(rows,indent=2))
print('READBACK_COMPLETE',len(rows),'EXPECTED',len(plans))
