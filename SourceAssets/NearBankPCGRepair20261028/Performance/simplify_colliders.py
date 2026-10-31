from pathlib import Path
import json,sys,itertools
R=Path(__file__).resolve().parent;P=R.parent;sys.path.insert(0,str(P/'Audit/pythonlib'))
import numpy as np
from scipy.spatial import HalfspaceIntersection,ConvexHull
baseline=json.loads((P/'Audit/saved_scene.json').read_text())['meshes'];plan=json.loads((P/'Repair/repair_plan.json').read_text());jobs=json.loads((R/'mesh_jobs.json').read_text());counts=[]
directions=np.array([d for d in itertools.product([-1,0,1],repeat=3) if any(d)],dtype=float);directions/=np.linalg.norm(directions,axis=1)[:,None]
oldjobs={j['asset']:j for j in json.loads((P/'Repair/mesh_jobs.json').read_text()) if j['kind']=='create'}
for mesh,path in plan['vehicle_collision_meshes'].items():
 v=np.array(baseline[mesh]['vertices']);axis=int(np.argmax(np.ptp(v[:,:2],axis=0)));split=np.linspace(v[:,axis].min(),v[:,axis].max(),4);vertices=[];triangles=[]
 for i in range(3):
  points=v[(v[:,axis]>=split[i]-8)&(v[:,axis]<=split[i+1]+8)];support=np.max(points@directions.T,axis=0)+.001
  corners=HalfspaceIntersection(np.column_stack([directions,-support]),points.mean(0)).intersections;h=ConvexHull(corners);offset=len(vertices);vertices.extend(corners.tolist());triangles.extend((h.simplices+offset).tolist())
 j=dict(oldjobs[path]);j.update(vertices_cm=vertices,triangles=triangles);jobs.append(j);counts.append(dict(asset=path,before_triangles=len(oldjobs[path]['triangles']),after_triangles=len(triangles)))
(R/'mesh_jobs.json').write_text(json.dumps(jobs,separators=(',',':')));(R/'collider_reduction.json').write_text(json.dumps(counts,indent=2));print(json.dumps(counts,indent=2))
