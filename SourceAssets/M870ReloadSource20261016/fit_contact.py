"""Small whole-palm contact registration; source articulation stays intact."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;d=np.load(O/'fit_inputs.npz');frames=(18,24,31);trees={}
for f in frames:
 tri=d[f'{f}_shell'][d['triangles']];cloud=[]
 for i in range(9):
  for j in range(9-i):
   a=i/8;b=j/8;cloud.append(tri[:,0]*a+tri[:,1]*b+tri[:,2]*(1-a-b))
 trees[f]=cKDTree(np.concatenate(cloud))
def transform(v,p):return Rotation.from_rotvec(p[3:]).apply(v)+p[:3]
def gaps(p):return {f:{n:float(trees[f].query(transform(d[f'{f}_{n}'],p),workers=1)[0].min()) for n in ('thumb','index','middle')} for f in frames}
def cost(p):
 g=gaps(p);value=sum((max(0,v-.001)/.001)**2 for row in g.values() for v in row.values())
 for f in frames:
  points=transform(d[f'{f}_all'],p);m=d[f'{f}_hand_to_shell'];v=(np.c_[points,np.ones(len(points))]@m.T)[:,:3]
  radius=np.linalg.norm(v[:,[0,2]],axis=1);inside=(v[:,1]>.006)&(v[:,1]<.054)
  penetration=np.maximum(0,.0088-radius[inside]);value+=40*np.mean((penetration/.001)**2) if len(penetration) else 0
 return value+.15*np.sum((p[:3]/.012)**2)+.15*np.sum((p[3:]/.2618)**2)
seed=np.zeros(6)
if (O/'contact_registration.json').exists():
 old=json.loads((O/'contact_registration.json').read_text());m=np.array(old['hand_local_matrix']);seed=np.r_[m[:3,3],Rotation.from_matrix(m[:3,:3]).as_rotvec()]
res=minimize(cost,seed,method='Powell',bounds=[(-.012,.012)]*3+[(-.2618,.2618)]*3,options={'maxiter':100,'xtol':1e-6,'ftol':1e-6})
p=res.x;m=np.eye(4);m[:3,:3]=Rotation.from_rotvec(p[3:]).as_matrix();m[:3,3]=p[:3]
report={'hand_local_matrix':m.tolist(),'translation_mm':(p[:3]*1000).tolist(),'rotation_vector_deg':np.degrees(p[3:]).tolist(),'before_mm':{f:{n:v*1000 for n,v in row.items()} for f,row in gaps(np.zeros(6)).items()},'after_mm':{f:{n:v*1000 for n,v in row.items()} for f,row in gaps(p).items()},'scope':'A constant whole-hand calibration in palm space; no finger curl, bone length, source timing or skin weight edits'}
(O/'contact_registration.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
