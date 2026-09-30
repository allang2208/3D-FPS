"""Fit only the 201 right upper sleeve to the accepted native arm weights."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
shirt=json.loads((O/'shirt_weights.json').read_text());bare=json.loads((O/'201_weights.json').read_text())
p=np.asarray(shirt['positions']);q=np.asarray(bare['positions']);faces=[]
for face,region in zip(bare['triangles'],bare['triangle_materials']):
 if region not in [0,1]:continue
 if all(q[i,0]>0 for i in face):faces.append(face)
tree=BVHTree.FromPolygons([Vector(v) for v in q],faces,all_triangles=True)
changed=[];target=[]
for i,(point,weights) in enumerate(zip(p,shirt['weights'])):
 # The distal forearm, wrist, fingers and entire left sleeve retain their data.
 upper=sum(w for n,w in weights.items() if n.startswith(('spine_','clavicle_r','upperarm_')))
 if point[0]<=0 or upper<1.e-6:continue
 hit,normal,fi,dist=tree.find_nearest(Vector(point))
 if fi is None or dist>8:raise RuntimeError('No corresponding right arm surface '+str(i))
 ids=faces[fi];a,b,c=q[ids];v0=b-a;v1=c-a;v2=np.array(hit)-a
 d00=v0@v0;d01=v0@v1;d11=v1@v1;d20=v2@v0;d21=v2@v1;den=d00*d11-d01*d01
 v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den
 bary=np.maximum([1-v-w,v,w],0);bary/=sum(bary);new={}
 for vi,mix in zip(ids,bary):
  for n,weight in bare['weights'][vi].items():new[n]=new.get(n,0)+float(mix*weight)
 new=dict(sorted(((n,w) for n,w in new.items() if w>1.e-6),key=lambda item:-item[1])[:8]);total=sum(new.values());new={n:w/total for n,w in new.items()}
 target.append({'vertex_id':shirt['vertex_ids'][i],'weights':new})
 changed.append({'vertex_id':shirt['vertex_ids'][i],'distance_cm':dist,'before':weights,'after':new})
 shirt['weights'][i]=new
(O/'shirt_fitted_weights.json').write_text(json.dumps(shirt,separators=(',',':')))
(O/'weight_edits.json').write_text(json.dumps(target,separators=(',',':')))
(O/'fit_report.json').write_text(json.dumps({'method':'Corresponding right native upperarm triangles, barycentric weight transfer; no pose/position/UV/normal edits','vertices_changed':len(changed),'maximum_source_distance_cm':max(x['distance_cm'] for x in changed),'edits':changed},indent=2))
print('ADS34_SLEEVE_FIT',len(changed),flush=True)
