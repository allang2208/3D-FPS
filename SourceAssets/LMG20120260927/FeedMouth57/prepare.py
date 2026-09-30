"""Extract connected, fixed receiver pieces crossing the new local opening."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
O=Path(__file__).parent
S=json.loads((O/'source.json').read_text())
C=json.load(gzip.open(O/'native.json.gz','rt'))
root=next(b for b in S['bones'] if b['name']=='WPN_root');r=root['rest'];R=Rotation.from_quat(r[3:7]).as_matrix()
rows=np.array(C['triangles'],int);ids=np.unique(rows[:,1:4]);raw=np.array([C['vertices'][str(i)]['p'] for i in ids])
p=(raw-r[:3])@R/np.array(r[7:]);t=np.searchsorted(ids,rows[:,1:4])
v,inv=np.unique(np.round(p,7),axis=0,return_inverse=True);f=inv[t]
edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
_,labels=connected_components(graph);face_labels=labels[f[:,0]]
lo=np.array([-.0128,.098,.052]);hi=np.array([.050,.171,.115])
q=v[f];touch=np.all(q.max(1)>lo,axis=1)&np.all(q.min(1)<hi,axis=1)
parts=[];remove=[];details=[]
for k in np.unique(face_labels[touch]):
 sel=np.where(face_labels==k)[0];ts=f[sel];used=np.unique(ts);points=v[used]
 original_ids=np.unique(rows[sel,1:4])
 if any(any(b!=root['index'] and w>1e-6 for b,w in C['vertices'][str(i)]['w']) for i in original_ids):
  continue
 n=np.array([C['normals'][str(rows[i,0])] for i in sel])@R
 entry={'name':'F57_ReceiverComponent_%02d'%int(k),'p':points.tolist(),'t':np.searchsorted(used,ts).tolist(),
        'mi':rows[sel,4].tolist(),'n':n.tolist(),'uv':[C['uvs'][str(rows[i,0])] for i in sel],
        'source_ids':rows[sel,0].tolist()}
 parts.append(entry);remove+=entry['source_ids']
 details.append({'name':entry['name'],'faces':len(sel),'slots':sorted({S['slots'][int(m)]['name'] for m in rows[sel,4]}),'min':points.min(0).tolist(),'max':points.max(0).tolist()})
with gzip.open(O/'patch_source.json.gz','wt') as z:json.dump(parts,z)
(O/'removals.json').write_text(json.dumps({'source_body_sha256':S['sha256'],'remove_triangle_ids':remove},indent=2))
(O/'authoring_inputs.json').write_text(json.dumps({'opening_min_root_m':lo.tolist(),'opening_max_root_m':hi.tolist(),'corner_radius_m':.002,'new_edge_bevel_m':.00022,'parts':details},indent=2))
print(json.dumps(details,indent=2))
