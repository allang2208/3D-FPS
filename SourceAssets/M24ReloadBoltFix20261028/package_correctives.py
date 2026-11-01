import sys,json
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O.parent/'M24LeftElbowReview20261028/PythonDeps'))
import numpy as np
N=np.load(O/'corrective_source.npz');D=json.loads((O/'corrective_source.json').read_text());G=json.loads((O/'geometry.json').read_text());shapes=np.load(O/'elbow_correctives.npz')
P=N['P'];T=N['T'];UV=N['UV'].copy();UV[:,:,1]=1-UV[:,:,1];UV=np.round(UV,5)
def side(weights):return 'l' if sum(x for n,x in weights.items() if n.endswith('_l'))>sum(x for n,x in weights.items() if n.endswith('_r')) else 'r'
lookup={}
for t,uv in zip(T,UV):lookup[(side(D['weights'][int(t[0])]),tuple(sorted(map(tuple,uv))))]={tuple(x):int(v) for x,v in zip(uv,t)}
mapping={}
for f in G['faces']:
 uv=np.round(f['uv'],5);key=(side(G['weights'][str(f['vertices'][0])]),tuple(sorted(map(tuple,uv))))
 if key not in lookup:raise RuntimeError('UV topology mismatch')
 for v,x in zip(f['vertices'],uv):mapping[int(v)]=lookup[key][tuple(x)]
axis=np.array([1,-1,1]);error=max(float(np.linalg.norm(np.array(G['positions'][str(v)])-P[i]*axis)) for v,i in mapping.items())
if error>.001:raise RuntimeError('Geometry coordinates differ '+str(error))
def normals(X):
 f=np.cross(X[T[:,1]]-X[T[:,0]],X[T[:,2]]-X[T[:,0]]);out=np.zeros_like(X)
 for k in range(3):np.add.at(out,T[:,k],f)
 return out/np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-12)
n0=normals(P);payload={}
for name in shapes.files:
 delta=shapes[name];nn=normals(P+delta);payload[name]=[[v,*map(float,delta[i]*axis),*map(float,n0[i]*axis),*map(float,nn[i]*axis)] for v,i in mapping.items() if np.linalg.norm(delta[i])>.0005]
temporary=O/'morph_payload.tmp.json';temporary.write_text(json.dumps({'path':G['path'],'sha256':G['sha256'],'geometry_error_cm':error,'morph_threshold_position_cm':.001,'morphs':payload}));temporary.replace(O/'morph_payload.json')
print('M24_MORPH_PAYLOAD',len(payload),'geometry_error_cm',error,flush=True)
