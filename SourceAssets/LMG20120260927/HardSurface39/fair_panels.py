"""Fit coherent existing hard-surface panels; keep relief edges and interfaces."""
import numpy as np,json
from pathlib import Path
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
O=Path(__file__).parent;report={}
for name in ['Receiver','Handguard']:
 d=np.load(O/(name+'.npz'));base=d['v'];f=d['f'];mid=d['mid'];v=base.copy();nv=len(v);nf=len(f);mask=np.zeros(nv);normal_target=np.zeros_like(v)
 cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]);area=np.linalg.norm(cross,axis=1);normal=cross/np.maximum(area[:,None],1e-15)
 edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);owner=np.tile(np.arange(nf),3);ee,inv,cnt=np.unique(edges,axis=0,return_inverse=True,return_counts=True);order=np.argsort(inv,kind='stable');start=np.r_[0,np.cumsum(cnt)[:-1]];ok=cnt==2;fa=owner[order[start[ok]]];fb=owner[order[start[ok]+1]]
 adjacency=coo_matrix((np.ones(len(ee)*2),(np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),shape=(nv,nv)).tocsr();degree=np.maximum(np.asarray(adjacency.sum(1)).ravel(),1)
 pinned=np.zeros(nv,bool);pinned[np.unique(ee[cnt!=2])]=True;pinned[np.unique(f[mid!=0])]=True
 # Actual part installation ends and receiver top rim never move.
 if name=='Receiver':pinned|=(v[:,1]<-.228)|(v[:,1]>.064)|(v[:,2]>.060)
 else:pinned|=(v[:,1]<-.446)|(v[:,1]>-.229)|((v[:,1]>-.381)&(v[:,2]<.050))
 changes=[]
 for axis in [0,2]:
  for sign in [-1,1]:
   use=(mid==0)&(normal[:,axis]*sign>.90)
   link=use[fa]&use[fb]&(np.sum(normal[fa]*normal[fb],axis=1)>.94)
   a,b=fa[link],fb[link];graph=coo_matrix((np.ones(len(a)*2),(np.r_[a,b],np.r_[b,a])),shape=(nf,nf));_,labels=connected_components(graph,directed=False)
   for label in np.unique(labels[use]):
    ids=np.flatnonzero(use&(labels==label))
    if len(ids)<35 or area[ids].sum()<.00012:continue
    vi=np.unique(f[ids]);vv=base[vi];center=np.median(vv,axis=0);_,_,vt=np.linalg.svd(vv-center,full_matrices=False);n=vt[-1];res=(vv-center)@n
    if abs(n[axis])<.96 or np.quantile(abs(res),.9)>.0014:continue
    support=np.bincount(f[ids].ravel(),minlength=nv);total=np.maximum(np.bincount(f.ravel(),minlength=nv),1);strength=np.clip((support/total-.35)/.65,0,1);strength[pinned]=0
    # One-ring taper preserves recess shoulders without freezing the whole patch.
    strength=np.minimum(strength,.35+.65*(adjacency@strength/degree));strength[pinned]=0
    v[vi]-=n[None]*np.clip((v[vi]-center)@n,-.0011,.0011)[:,None]*strength[vi,None]
    chosen=vi[strength[vi]>mask[vi]];normal_target[chosen]=n*np.sign(n[axis])*sign
    mask[vi]=np.maximum(mask[vi],strength[vi])
    changes.append({'axis':axis,'side':sign,'faces':len(ids),'rms_before_mm':float(np.sqrt(np.mean(res**2))*1000),'rms_after_mm':float(np.sqrt(np.mean(((v[vi]-center)@n)**2))*1000)})
 delta=v-base;length=np.linalg.norm(delta,axis=1);delta*=np.minimum(1,.0011/np.maximum(length,1e-12))[:,None];v=base+delta
 np.savez_compressed(O/(name+'_fair.npz'),v=v,mask=mask,normal_target=normal_target)
 report[name]={'patches':changes,'moved_vertices':int((np.linalg.norm(delta,axis=1)>1e-8).sum()),'max_move_mm':float(np.linalg.norm(delta,axis=1).max()*1000),'pinned_vertices':int(pinned.sum())}
(O/'panels.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:{'patches':len(v['patches']),'moved_vertices':v['moved_vertices'],'max_move_mm':v['max_move_mm']} for k,v in report.items()}))
