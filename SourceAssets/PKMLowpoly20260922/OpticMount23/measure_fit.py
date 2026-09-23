"""Measure only the requested cover/rail/optic interfaces from source vertices."""
import json, numpy as np
from pathlib import Path
O=Path(__file__).parent;d=json.loads((O/'source_geometry.json').read_text())
cover=next(p for p in d['parts'] if p['name']=='PKM_Part_043')
verts=np.array(cover['vertices']);tris=verts[np.array(cover['triangles'])]
def surface(x,y):
 result=[]
 for t in tris:
  a,b,c=t;matrix=np.column_stack((b[:2]-a[:2],c[:2]-a[:2]))
  if abs(np.linalg.det(matrix))<1e-12:continue
  u,v=np.linalg.solve(matrix,np.array([x,y])-a[:2])
  if u>=-1e-6 and v>=-1e-6 and u+v<=1.000001:result.append(float(a[2]+u*(b[2]-a[2])+v*(c[2]-a[2])))
 return max(result) if result else None
result={'cover_surface_samples':[],'optic_feet':{}}
for y in [.012,.025,.055,.085,.11,.122,.127]:
 result['cover_surface_samples'].append({'y':y,'z_at_x':{str(x):surface(x,y) for x in [-.018,-.012,0,.012,.018]}})
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x']:
 points=np.concatenate([np.array(r['vertices']) for r in d['optics'][key]])
 bottom=points[points[:,2]<.005]
 gy=.05 if key=='lpvo_1_6x' else .06 if key=='prism_scope_2x' else .07
 result['optic_feet'][key]={'base_source_min':bottom.min(axis=0).tolist(),'base_source_max':bottom.max(axis=0).tolist(),
  'mounted_foot_y':[float(gy-bottom[:,0].max()),float(gy-bottom[:,0].min())]}
(O/'fit_measurements.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=1))
