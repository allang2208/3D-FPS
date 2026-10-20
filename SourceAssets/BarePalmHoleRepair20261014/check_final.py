import json,numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
from analyze_surface import analyze
from plan_repair import palm_weight
R=Path(__file__).resolve().parent
plans={v['path']:v for v in json.loads((R/'triangulated_plan.json').read_text())};rows=[]
for file in (R/'Final').glob('*.json'):
 d=json.loads(file.read_text());entry=plans[d['path']];old=json.loads(Path(entry['snapshot']).read_text());r=analyze(d)
 v=np.array(d['positions']);t=np.array(d['triangles']);n=np.array(d['normals'])
 holes=[c for c in r['boundary_components'] if max(c['span'])<.5 and np.mean([palm_weight(d['weights'][i]) for i in c['vertices']])>.65]
 tree=cKDTree(old['positions']);dist,nearest=tree.query(v)
 weight_diff=max(sum(abs(ws.get(k,0)-old['weights'][j].get(k,0)) for k in set(ws)|set(old['weights'][j])) for ws,j in zip(d['weights'],nearest))
 row=dict(path=d['path'],small_palm_openings=len(holes),seam_weight_splits=len(r['seam_weight_splits']),
  max_surface_vertex_movement_cm=float(dist.max()),max_original_weight_difference=float(weight_diff))
 if 'SprintV1' in d['path']:
  # The actual hammer mesh has the canonical tool reference, so this also
  # checks the new triangles' front-facing winding without pose ambiguity.
  signature=lambda ps:tuple(sorted(tuple(np.round(p,3)) for p in ps))
  patches=set()
  for patch in entry['patches']:
   points=[old['positions'][old['triangles'][c['triangle']][c['a']]] for c in patch['corners']]
   for tri in patch['fill_triangles']:patches.add(signature([points[i] for i in tri]))
  sign=np.einsum('ij,ij->i',np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]),n.mean(1));orientation=np.sign(np.median(sign))
  found=[i for i,tri in enumerate(t) if signature(v[tri]) in patches]
  row.update(patch_triangles_read_back=len(found),expected_patch_triangles=len(patches),patch_backfaces=sum(int(sign[i]*orientation< -1e-8) for i in found))
 rows.append(row);print(json.dumps(row))
(R/'final_findings.json').write_text(json.dumps(rows,indent=2))
assert len(rows)==len(plans)
assert all(r['small_palm_openings']==0 and r['seam_weight_splits']==0 and r['max_surface_vertex_movement_cm']<.0001 and r['max_original_weight_difference']<.0001 for r in rows)
hammer=next(r for r in rows if 'SprintV1' in r['path'])
assert hammer['patch_backfaces']==0 and hammer['patch_triangles_read_back']==hammer['expected_patch_triangles']
print('PALM_FINAL_TOPOLOGY_AND_BINDING_READBACK_COMPLETE',len(rows))
