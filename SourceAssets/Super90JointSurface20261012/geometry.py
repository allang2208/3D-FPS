import gzip,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent
def load(name):return json.loads(gzip.decompress((O/name).read_bytes()))
def mat(b):
 m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position'];return m
def skin(d,row,p=None,n=None):
 p=np.array(d['positions']) if p is None else p
 out=np.zeros_like(p); normal=np.zeros_like(n) if n is not None else None
 for bone,b in d['bones'].items():
  weights=np.array([w.get(bone,0.) for w in d['weights']]);ids=np.flatnonzero(weights)
  if not len(ids):continue
  m=mat(row['bones'][bone])@np.linalg.inv(mat(b))
  out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*weights[ids,None]
  if n is not None:normal[ids]+=(n[ids]@np.linalg.inv(m[:3,:3]))*weights[ids,None]
 if n is not None:normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-10)
 return (out,normal) if n is not None else out
def vertex_normals(p,t):
 f=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]])
 n=np.zeros_like(p)
 for j in range(3):np.add.at(n,t[:,j],f)
 return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-10)
if __name__=='__main__':
 d=load('full_before.json.gz');poses=load('poses.json.gz')
 shots=[('idle',0),('reload_full',45),('reload_full',115)]
 np.savez_compressed(O/'review_before.npz',triangles=d['triangles'],materials=d['materials'],**{f'p{i}':skin(d,poses[n]['rows'][i0]) for i,(n,i0) in enumerate(shots)})
 (O/'shots.json').write_text(json.dumps([dict(label=n,time=poses[n]['rows'][i]['time'],bones=poses[n]['rows'][i]['bones']) for n,i in shots]))
