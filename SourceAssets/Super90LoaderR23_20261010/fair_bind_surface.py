"""Local, volume-preserving fairing of the left elbow bind-surface fold."""
import json
import numpy as np
from scipy.sparse import csr_matrix,diags
from pathlib import Path
O=Path(__file__).parent;g=json.loads((O/'geometry.json').read_text())
m=g['meshes']['Super90_V7_M4_BareArmsV6'];v=np.array(m['positions']);rest={n:np.array(x) for n,x in g['rest'].items()}
a=rest['upperarm_l'][:3,3];e=rest['lowerarm_l'][:3,3];axis=e-a;axis/=np.linalg.norm(axis)
station=(v-e)@axis
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
mask=smooth((station+.10)/.04)*(1-smooth((station-.055)/.04))*(v[:,0]<-.23)
edges=set()
for face in m['faces']:
    for i,x in enumerate(face):
        y=face[(i+1)%len(face)];edges.add((x,y));edges.add((y,x))
rows,cols=zip(*edges);A=csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(v),len(v)));A=diags(1/np.maximum(1,np.asarray(A.sum(axis=1)).ravel()))@A
new=v.copy()
for _ in range(100):
    for amount in (.5,-.53):new+=amount*mask[:,None]*(A@new-new)
edits=[dict(index=int(i),before=v[i].tolist(),after=new[i].tolist()) for i in np.flatnonzero(np.linalg.norm(new-v,axis=1)>1e-6)]
report=dict(reason='Local Taubin fairing of left elbow bind fold; original topology, weights, UVs and wrist/hand retained',
    edited_vertices=len(edits),max_displacement_mm=float(np.linalg.norm(new-v,axis=1).max()*1000),edits=edits,runtime_tested=False)
(O/'bind_surface.json').write_text(json.dumps(report,separators=(',',':')))
print('LEFT_ELBOW_BIND_FAIRING',len(edits),report['max_displacement_mm'],flush=True)
