"""Recover original body corner data in each measured, already-authored host frame."""
import json,itertools,numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
O=Path(__file__).parent;X=O/'Working';D=json.loads((O/'inputs.json').read_text())
S=np.load(X/'original.npz');sp=S['positions'];st=S['triangles'];sc=sp[st].mean(axis=1);ct=cKDTree(sc)
sv=np.unique(np.round(sp,9),axis=0);sm=sv.mean(axis=0);_,sb=np.linalg.eigh(np.cov(sv.T));sample=sv[::3]
R={}
def align(a,b):
 am=a.mean(axis=0);bm=b.mean(axis=0);u,s,vt=np.linalg.svd((a-am).T@(b-bm));r=vt.T@u.T
 if np.linalg.det(r)<0:vt[-1]*=-1;r=vt.T@u.T
 return r,bm-am@r.T
for key in D['assets']:
 T=np.load(X/(key+'.npz'));p=T['positions'];t=T['triangles'];body=np.isin(T['mids'],T['body_slots']);ids=np.flatnonzero(body)
 tv=np.unique(np.round(p[np.unique(t[body])],9),axis=0);tm=tv.mean(axis=0);_,tb=np.linalg.eigh(np.cov(tv.T));tree=cKDTree(tv)
 choices=[]
 for signs in itertools.product((-1,1),repeat=3):
  r=tb@np.diag(signs)@sb.T
  if np.linalg.det(r)<0:continue
  tr=tm-sm@r.T
  for it in range(35):
   q=sample@r.T+tr;dist,idx=tree.query(q);mask=dist<=np.quantile(dist,.8)
   rr,tt=align(q[mask],tv[idx[mask]]);r=rr@r;tr=tr@rr.T+tt
   if np.max(abs(rr-np.eye(3)))<1e-10 and np.max(abs(tt))<1e-10:break
  dist,idx=tree.query(sv@r.T+tr);choices.append((float(np.quantile(dist,.8)),r,tr))
 score,r,tr=min(choices,key=lambda v:v[0]);q=sv@r.T+tr;dist,idx=tree.query(q);mask=dist<max(2e-6,np.quantile(dist,.8)*2)
 # Recover the authored near-rigid matrix, including sub-float root-frame scale.
 fit=np.linalg.lstsq(np.column_stack((sv[mask],np.ones(mask.sum()))),tv[idx[mask]],rcond=None)[0];a=fit[:3].T;tr=fit[3]
 scales=np.linalg.svd(a,compute_uv=False)
 if max(abs(scales-1))>.002:raise RuntimeError('Unexpected body scaling '+key+' '+str(scales))
 cp=(p-tr)@np.linalg.inv(a).T;centers=cp[t[body]].mean(axis=1);dist,nearest=ct.query(centers)
 target=cp[t[body]];source=sp[st[nearest]];errors=np.linalg.norm(target[:,:,None,:]-source[:,None,:,:],axis=3);perm=errors.argmin(axis=2)
 exact=(errors.min(axis=2).max(axis=1)<2e-6)&np.all(np.sort(perm,axis=1)==[0,1,2],axis=1)
 uv=T['uv0'].copy();norm=T['normals'].copy();norm_matrix=np.linalg.inv(a).T
 uv[ids[exact]]=S['uv0'][nearest[exact,None],perm[exact]]
 ns=S['normals'][nearest[exact,None],perm[exact]]@norm_matrix.T;ns/=np.linalg.norm(ns,axis=2,keepdims=True);norm[ids[exact]]=ns
 interpolated=0;caps=[]
 for j in np.flatnonzero(~exact):
  points=target[j];_,candidates=ct.query(points.mean(axis=0),k=64);best=None
  for si in candidates:
   tri=sp[st[si]];e0=tri[1]-tri[0];e1=tri[2]-tri[0];basis=np.stack((e0,e1),axis=1)
   bc=np.linalg.lstsq(basis,(points-tri[0]).T,rcond=None)[0].T;weights=np.column_stack((1-bc.sum(axis=1),bc));proj=weights@tri
   err=np.linalg.norm(proj-points,axis=1).max()
   if weights.min()>=-.002 and weights.max()<=1.002 and err<2e-6:
    best=(si,weights);break
  tid=ids[j]
  if best:
   si,w=best;uv[tid]=w@S['uv0'][si];n=(w@S['normals'][si])@norm_matrix.T;n/=np.linalg.norm(n,axis=1,keepdims=True);norm[tid]=n;interpolated+=1
  else:
   # Authored mouth closure has no source surface: preserve its geometry/normals,
   # put its UV on the untouched neutral corner of the original normal atlas.
   if points[:,0].max()>.006:raise RuntimeError('Unmatched original body face '+key+' '+str(tid)+' '+str(points.tolist()))
   uv[tid]=np.array([[.992,.992],[.998,.992],[.992,.998]]);caps.append(int(tid))
 np.savez_compressed(X/(key+'_plan.npz'),body_triangles=ids,uv0=uv,normals=norm,transform=np.vstack((np.column_stack((a,tr)),[0,0,0,1])))
 residual=tree.query(sv@a.T+tr)[0]
 R[key]={'body_triangles':len(ids),'exact_source_triangles':int(exact.sum()),'interpolated_cut_triangles':interpolated,'authored_mouth_cap_triangles':caps,'transform':np.vstack((np.column_stack((a,tr)),[0,0,0,1])).tolist(),'scale_singular_values':scales.tolist(),'matched_vertex_fit_p80_mm':float(np.quantile(residual,.8)*1000),'corner_match_max_mm':float(errors.min(axis=2).max(axis=1)[exact].max()*1000),'preserve_nonbody_from_current_export':True}
 (O/'matches.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('MATCHED',key,len(ids),int(exact.sum()),interpolated,len(caps),'fit_mm',R[key]['matched_vertex_fit_p80_mm'],flush=True)
