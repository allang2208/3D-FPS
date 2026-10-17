"""Register complete source poses to the native shell at five contact keys."""
import json,numpy as np
from pathlib import Path
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;d=np.load(O/'fit_inputs.npz');frames=(18,25,31,38,44)
def transform(v,p):return Rotation.from_rotvec(p[3:]).apply(v)+p[:3]
old=json.loads((O/'contact_registration.json').read_text());m=np.array(old['hand_local_matrix']);seed=np.r_[m[:3,3],Rotation.from_matrix(m[:3,:3]).as_rotvec()]
result={'scope':'Five rigid whole-hand contact keys. Original source finger animation is unchanged. Release blends calibration back to the next source grab.','keys':[]}
for f in frames:
 tri=d[f'{f}_shell'][d['triangles']];cloud=[]
 for i in range(9):
  for j in range(9-i):
   a=i/8;b=j/8;cloud.append(tri[:,0]*a+tri[:,1]*b+tri[:,2]*(1-a-b))
 tree=cKDTree(np.concatenate(cloud));roles=('index','middle') if f==25 else ('thumb','index','middle')
 def gaps(p):return {n:float(tree.query(transform(d[f'{f}_{n}'],p),workers=1)[0].min()) for n in ('thumb','index','middle')}
 def cost(p):
  g=gaps(p);val=sum((max(0,g[n]-.0008)/.001)**2 for n in roles)
  points=transform(d[f'{f}_all'],p);m=d[f'{f}_hand_to_shell'];v=(np.c_[points,np.ones(len(points))]@m.T)[:,:3]
  radius=np.linalg.norm(v[:,[0,2]],axis=1);inside=(v[:,1]>.006)&(v[:,1]<.054);penetration=np.maximum(0,.0088-radius[inside])
  return val+(50*np.mean((penetration/.001)**2) if len(penetration) else 0)+.08*np.sum((p[:3]/.012)**2)+.08*np.sum((p[3:]/.2618)**2)+.12*np.sum(((p-seed)/np.r_[[.012]*3,[.2618]*3])**2)
 opt=minimize(cost,seed,method='Powell',bounds=[(-.015,.015)]*3+[(-.2618,.2618)]*3,options={'maxiter':100,'xtol':1e-6,'ftol':1e-6})
 p=opt.x;m=np.eye(4);m[:3,:3]=Rotation.from_rotvec(p[3:]).as_matrix();m[:3,3]=p[:3]
 result['keys'].append({'source_phase':12*(f-18)/26,'target_frame':f,'matrix':m.tolist(),'translation_mm':(p[:3]*1000).tolist(),'rotation_vector_deg':np.degrees(p[3:]).tolist(),'roles':roles,'gaps_mm':{n:v*1000 for n,v in gaps(p).items()}})
 seed=p
(O/'contact_curve.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
