from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeSVDReferenceR2_20261019'))
from surface import *
O=HERE;G=np.array(glove['positions']);T=np.array(glove['triangles'])
def normals(v):
    f=np.cross(v[T[:,1]]-v[T[:,0]],v[T[:,2]]-v[T[:,0]]);n=np.zeros_like(v)
    for k in range(3):np.add.at(n,T[:,k],f)
    return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-10)
base=normals(G);fields=np.load(O/'glove-correctives.npz');morphs={}
for name in fields.files:
    delta=fields[name];target=G+delta;nd=normals(target)-base
    changed=np.flatnonzero((np.linalg.norm(delta,axis=1)>.00001)|(np.linalg.norm(nd,axis=1)>.001))
    morphs[name]=[[int(i),*target[i].tolist(),*nd[i].tolist()] for i in changed]
(O/'glove-payload.json').write_text(json.dumps({'path':glove['path'],'sha256':glove['sha256'],'positions':G.tolist(),'morphs':morphs},separators=(',',':')))
print('Prepared',len(morphs),'glove corrective fields',flush=True)
