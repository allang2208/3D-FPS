from pathlib import Path
import json,pickle,numpy as np
from motion import *
from support_pose import apply_support
r=Path(__file__).resolve().parent;g=pickle.load(open(r/'geometry.pkl','rb'));m=pickle.load(open(r/'m249_inputs.pkl','rb'))
names=m['names'];parents={n:(names[p] if p>=0 else None) for n,p in zip(names,m['parents'])};B={n:matrix(v) for n,v in zip(names,m['bind'])};L={n:matrix(v) for n,v in zip(names,m['frames'][0])};H=compose(names,parents,L)
params=json.loads((r/'hold_fit.json').read_text())['parameters'];out=apply_support(H,L,names,parents,B,H,params)
v=np.array(g['vertices']);p=np.zeros_like(v)
for j,n in enumerate(names):
    ids=np.array([i for i,ws in enumerate(g['weights']) if any(b==j for b,w in ws)])
    if not len(ids):continue
    ws=np.array([sum(w for b,w in g['weights'][i] if b==j) for i in ids]);p[ids]+=(np.c_[v[ids],np.ones(len(ids))]@(out[n]@np.linalg.inv(B[n])).T)[:,:3]*ws[:,None]
old=pickle.load(open(r/'fitted_surface.pkl','rb'));legs=old['0.0']['legs']
pickle.dump({'0.0':dict(vertices=p,legs=legs)},open(r/'hold_surface.pkl','wb'))
pickle.dump(out,open(r/'hold_world.pkl','wb'))
print('SUPPORT_HOLD_READY')
