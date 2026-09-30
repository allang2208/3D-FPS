"""Local fairing of the current receiver/cover, preserving source seams and UVs."""
import json,numpy as np
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
O=Path(__file__).parent;(O/'Work').mkdir(exist_ok=True)
report=[]
for name,cap in [('Receiver',.0011),('TopCover',.0008),('FrontSightBase_Fitted',.0005)]:
 old=np.load(O.parent/'Surface32/Work'/(name+'.npz'));s32=np.load(O.parent/'Surface32/Work'/(name+'_edited.npz'))
 p=s32['vertices'].copy();base=p.copy();f=old['faces'];mi=old['material_ids'];n=len(p)
 def normals(v):
  q=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);area=np.linalg.norm(q,axis=1);return q/np.maximum(area[:,None],1.e-16),area
 nf,area=normals(p);surface=mi==0
 ed=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);owner=np.tile(np.arange(len(f)),3)
 edges,inv,cnt=np.unique(ed,axis=0,return_inverse=True,return_counts=True);ix=np.argsort(inv,kind='stable');start=np.r_[0,np.cumsum(cnt)[:-1]];valid=cnt==2;fa=owner[ix[start[valid]]];fb=owner[ix[start[valid]+1]]
 graph=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(n,n)).tocsr();degree=np.maximum(np.asarray(graph.sum(1)).ravel(),1)
 fixed=np.zeros(n,bool);fixed[np.unique(f[~surface])]=True;fixed[np.unique(edges[cnt!=2])]=True
 sharp=(np.sum(nf[fa]*nf[fb],axis=1)<np.cos(np.radians(65)))|(mi[fa]!=mi[fb]);fixed[np.unique(edges[valid][sharp])]=True
 influence=(~fixed).astype(float)
 for _ in range(2):influence=np.minimum(influence,graph@influence/degree)
 for _ in range(18):
  for amount in [.42,-.44]:
   step=(graph@p/degree[:,None]-p)*influence[:,None]*amount
   delta=p+step-base;delta*=np.minimum(1,cap/np.maximum(np.linalg.norm(delta,axis=1),1.e-14))[:,None];p=base+delta
 # Segment coherent original panel faces by direction; grooves and inclined
 # perimeter faces cannot bridge separate flat islands.
 nf,area=normals(p);centers=p[f].mean(1);flattened=[];flatmask=np.zeros(n)
 for axis in ([0] if name=='Receiver' else [0,2]):
  for sign in [-1,1]:
   use=surface&(nf[:,axis]*sign>.93)
   links=use[fa]&use[fb]&(np.sum(nf[fa]*nf[fb],axis=1)>.9)
   a,b=fa[links],fb[links];g=coo_matrix((np.ones(len(a)*2),(np.r_[a,b],np.r_[b,a])),shape=(len(f),len(f))).tocsr();_,labels=connected_components(g)
   for label in np.unique(labels[use]):
    ids=np.flatnonzero(use&(labels==label))
    if len(ids)<25 or area[ids].sum()<.00010:continue
    vi=np.unique(f[ids]);v=p[vi];center=np.median(v,axis=0);_,_,vt=np.linalg.svd(v-center,full_matrices=False);normal=vt[-1]
    if abs(normal[axis])<.96 or np.quantile(abs((v-center)@normal),.9)>.0016:continue
    support=np.bincount(f[ids].ravel(),minlength=n);total=np.maximum(np.bincount(f.ravel(),minlength=n),1);alpha=np.clip((support/total-.45)/.55,0,1)*influence
    p[vi]-=normal[None]*((p[vi]-center)@normal)[:,None]*alpha[vi,None]*.92;flatmask[vi]=np.maximum(flatmask[vi],alpha[vi])
    flattened.append({'axis':axis,'side':sign,'faces':len(ids)})
 delta=p-base;delta*=np.minimum(1,cap/np.maximum(np.linalg.norm(delta,axis=1),1.e-14))[:,None];p=base+delta
 np.savez_compressed(O/'Work'/(name+'.npz'),vertices=p,flatmask=flatmask)
 report.append({'part':name,'source':'Surface32','changed_vertices':int((np.linalg.norm(delta,axis=1)>1e-8).sum()),'max_delta_mm':float(np.linalg.norm(delta,axis=1).max()*1000),'planar_regions':flattened})
(O/'fairing.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
