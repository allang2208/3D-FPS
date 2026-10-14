import json
from pathlib import Path
import numpy as np
O=Path(__file__).parent
for kind in ('phantom','balanced','stable'):
 with (O/'Input'/(kind+'.bin')).open('rb') as f:
  h=json.loads(f.readline());nv,nt=h['vertices'],h['triangles'];p=np.fromfile(f,'<f4',nv*3).reshape(-1,3);t=np.fromfile(f,'<i4',nt*3).reshape(-1,3);np.fromfile(f,'<i4',nt);np.fromfile(f,'<f4',nt*9);uv=np.fromfile(f,'<f4',nt*6).reshape(-1,3,2)
 _,ix,iv=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);P=p[ix];T=iv[t];mask=np.zeros(len(P));np.maximum.at(mask,T.ravel(),uv[:,:,0].ravel())
 near=np.any(uv[:,:,0]>1e-5,axis=1);tri=T[near];e=np.unique(np.sort(np.r_[tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]],1),axis=0)
 print(kind,'neck_tris',sum(near),'levels',[(float(v),int(sum(np.isclose(mask,v,atol=1e-5)&(P[:,2]>-2.9)))) for v in np.unique(np.round(mask,4))])
 for level in (.035,.43,1.):
  on=np.isclose(mask,level,atol=1e-4);ee=e[on[e[:,0]]&on[e[:,1]]];counts=np.bincount(ee.ravel(),minlength=len(P));print(level,'edges',len(ee),'degrees',np.unique(counts[on],return_counts=True))
