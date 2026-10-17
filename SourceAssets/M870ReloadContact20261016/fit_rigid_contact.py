"""Bounded whole-hand registration; no digit or bone-length variables."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;d=np.load(O/'fit_inputs.npz')
tri=d['shell'][d['triangles']]
surface=[]
for i in range(9):
 for j in range(9-i):
  a=i/8;b=j/8;surface.append(tri[:,0]*a+tri[:,1]*b+tri[:,2]*(1-a-b))
tree=cKDTree(np.concatenate(surface));centre=d['shell'].mean(axis=0)
def transform(v,p):return Rotation.from_rotvec(p[3:]).apply(v-centre)+centre+p[:3]
def gaps(p):return {n:float(tree.query(transform(d[n],p),workers=1)[0].min()) for n in ('thumb','index','middle','ring')}
def cost(p):
 g=gaps(p);v=transform(d['all'],p);radius=np.linalg.norm(v[:,[0,2]],axis=1)
 inside=(v[:,1]>.006)&(v[:,1]<.054)
 penetration=np.maximum(0,.0088-radius[inside])
 return sum((max(0,g[n]-.0008)/.001)**2 for n in ('thumb','index','middle'))+12*np.mean((penetration/.001)**2)+.06*np.sum((p[:3]/.008)**2)+.06*np.sum((p[3:]/.1745)**2)
res=minimize(cost,np.zeros(6),method='Powell',bounds=[(-.008,.008)]*3+[(-.1745,.1745)]*3,options={'maxiter':120,'xtol':1.e-6,'ftol':1.e-6})
p=res.x;rot=Rotation.from_rotvec(p[3:]).as_matrix();m=np.eye(4);m[:3,:3]=rot;m[:3,3]=centre+p[:3]-rot@centre
out={'matrix':m.tolist(),'translation_mm':(p[:3]*1000).tolist(),'rotation_vector_deg':np.degrees(p[3:]).tolist(),
 'before_gap_mm':{k:v*1000 for k,v in gaps(np.zeros(6)).items()},'after_gap_mm':{k:v*1000 for k,v in gaps(p).items()},
 'scope':'One rigid hand transform, translation bound 8 mm per axis and rotation-vector bound 10 degrees per axis; no finger edits.'}
(O/'rigid_contact.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
