import json,sys
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
O=Path(__file__).parent;sys.path.insert(0,str(O));import geometry as G
h,raw,p,t,m,uv,n,bone=G.body();out={}
def parts(p,t,sel):
    faces=t[sel];vi,inv=np.unique(faces,return_inverse=True)
    co=p[vi];unique,wi=np.unique(np.round(co,6),axis=0,return_inverse=True);wt=wi[inv.reshape(-1,3)]
    edges=np.concatenate((wt[:,[0,1]],wt[:,[1,2]],wt[:,[2,0]]))
    _,labels=connected_components(coo_matrix((np.ones(len(edges)),(edges[:,0],edges[:,1])),shape=(len(unique),len(unique))),directed=False)
    fc=labels[wt[:,0]];result=[]
    for k in np.unique(fc):
        ts=faces[fc==k];points=p[ts];count=len(ts)
        if count<12:continue
        result.append({'faces':count,'min_mm':(points.min((0,1))*1000).round(2).tolist(),'max_mm':(points.max((0,1))*1000).round(2).tolist()})
    return sorted(result,key=lambda x:-x['faces'])
for name in ['M_A762_Receiver','M_A762_FactoryRearGrip','M_A762_FrontAssembly_Rebuilt']:
    out[name]=parts(p,t,m==h['slots'].index(name))
for key in ['balanced_reargrip','stable_antislip_reargrip','phantom_reargrip']:
    ah,ap,at,am,au,an=G.read(key);ap=ap*G.FLIP
    out[key]=parts(ap,at,np.ones(len(at),bool))
(O/'Inspection/components.json').write_text(json.dumps(out,indent=2))
for key,value in out.items():print(key,json.dumps(value[:12]),flush=True)
