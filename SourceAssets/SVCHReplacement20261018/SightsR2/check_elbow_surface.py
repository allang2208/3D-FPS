import runpy,json
from pathlib import Path
import numpy as np,trimesh
O=Path(__file__).parent;e=runpy.run_path(str(O/'author_elbow_clearance.py'))
profile=json.loads((O/'profile_elbow_clearance.json').read_text());clip=next(x for x in profile['clips'] if x['base']==e['c']['path']);report=[]
for frame in [276,280,284,300,315,330,340,344,348,360]:
 w,_=e['world_at'](frame,clip);v=e['skin'](w,np.arange(len(e['vertices'])));mesh=trimesh.Trimesh(v,e['a']['triangles'],process=True);query=e['rear'][::25];sd=np.concatenate([trimesh.proximity.signed_distance(mesh,query[i:i+64]) for i in range(0,len(query),64)])
 row={'frame':frame,'inside_samples':int((sd>.01).sum()),'max_penetration_cm':float(max(0,sd.max())),'min_surface_distance_cm':float(abs(sd).min())};report.append(row);print(json.dumps(row),flush=True)
(O/'elbow_surface_check.json').write_text(json.dumps(report,indent=2))
