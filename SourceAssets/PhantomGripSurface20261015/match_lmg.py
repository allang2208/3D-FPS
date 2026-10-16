import numpy as np,json
from scipy.spatial import cKDTree
from pathlib import Path
O=Path(__file__).parent;X=O/'Working';a=np.load(X/'LMG201.npz');s=np.load(X/'LMG201_source_uv4.npz');p=a['positions'];t=a['triangles'];sp=s['positions'];st=s['triangles'];uv=s['uv4'];q=p[t];sq=sp[st]
dist,ids=cKDTree(sq.mean(1)).query(q.mean(1));e=np.linalg.norm(q[:,:,None,:]-sq[ids,None,:,:],axis=3);perm=e.argmin(2);err=e.min(2).max(1);matched=(err<2e-6)&np.all(np.sort(perm,axis=1)==[0,1,2],axis=1)
out=a['uv4'].copy();out[matched]=uv[ids[matched,None],perm[matched]]
# Surface01 moved a few vertices by under 0.08 mm; the nearest face still supplies
# its original transition mask when the triangles are uniquely paired.
near=(err<.0002)&np.all(np.sort(perm,axis=1)==[0,1,2],axis=1);out[near]=uv[ids[near,None],perm[near]]
unmatched=~near;print('LMG_MASK_MATCH',int(matched.sum()),int(near.sum()),int(unmatched.sum()),'source_nonzero',int((uv[:,:,0]>.01).any(1).sum()),'restored',int((out[:,:,0]>.01).any(1).sum()),flush=True)
if (unmatched&(q[:,:,2].max(1)>-.031)).any():raise RuntimeError('Cannot restore a connector mask face')
np.save(X/'LMG201_restored_uv4.npy',out)
(O/'lmg_mask_match.json').write_text(json.dumps({'exact_faces':int(matched.sum()),'matched_faces':int(near.sum()),'unmatched_lower_faces_retained':int(unmatched.sum()),'restored_transition_faces':int((out[:,:,0]>.01).any(1).sum())},indent=2))
