"""Local normal-projection fairing; preserve vents, seams and generated silhouette."""
from pathlib import Path
import json,numpy as np
from scipy.sparse import coo_matrix
R=Path(__file__).resolve().parent
d=np.load(R/'source_surface.npz');v0=d['vertices'];f0=d['faces'];uv=d['uv'];old=d['normals']
# UV-split vertices remain distinct in output. Work on shared geometry positions.
_,first,inv=np.unique(np.round(v0,7),axis=0,return_index=True,return_inverse=True)
v=v0[first].copy();base=v.copy();f=inv[f0];nf=len(f);nv=len(v)
def fn(p):
 q=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
 area=np.linalg.norm(q,axis=1)
 return q/np.maximum(area[:,None],1e-15),area
n0,ar=fn(v);c=v[f].mean(1)
# Semantic surface scope: receiver / guard / upper-cover, outside the pouch,
# grip, stock and front-sight assembly. Large opposing faces never mix.
region=(c[:,0]>-.457)&(c[:,0]<.527)&(c[:,2]>-.004)&(c[:,2]<.188)
region &= ~((c[:,0]>.015)&(c[:,0]<.217)&(c[:,1]<-.033)&(c[:,2]<.148))
e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
ef=np.tile(np.arange(nf),3)
es,ei,counts=np.unique(e,axis=0,return_inverse=True,return_counts=True)
order=np.argsort(ei,kind='stable');starts=np.r_[0,np.cumsum(counts)[:-1]]
man=counts==2;fa=ef[order[starts[man]]];fb=ef[order[starts[man]+1]];ee=es[man]
dot=np.sum(n0[fa]*n0[fb],axis=1)
feature=(dot<np.cos(np.radians(35)))|(region[fa]!=region[fb])
pin=np.zeros(nv,bool);pin[np.unique(es[~man])]=True;pin[np.unique(ee[feature])]=True
pin[np.unique(f[~region])]=True
adj=coo_matrix((np.ones(len(es)*2),(np.r_[es[:,0],es[:,1]],np.r_[es[:,1],es[:,0]])),shape=(nv,nv)).tocsr()
deg=np.maximum(np.asarray(adj.sum(1)).ravel(),1);influence=(~pin).astype(float)
for _ in range(3):influence=np.minimum(influence,adj@influence/deg)
influence[pin]=0
valid=(~feature)&region[fa]&region[fb];a=fa[valid];b=fb[valid]
dist=np.linalg.norm(c[a]-c[b],axis=1);spatial=np.exp(-.5*(dist/.007)**2);filtered=n0.copy()
for _ in range(7):
 w=spatial*np.exp(-(1-np.clip(np.sum(filtered[a]*filtered[b],axis=1),-1,1))/.016)
 accum=filtered.copy();den=np.ones(nf)
 np.add.at(accum,a,filtered[b]*w[:,None]);np.add.at(accum,b,filtered[a]*w[:,None]);np.add.at(den,a,w);np.add.at(den,b,w)
 filtered=accum/den[:,None];filtered/=np.maximum(np.linalg.norm(filtered,axis=1,keepdims=True),1e-15)
weights=np.clip(np.sqrt(ar/max(np.median(ar),1e-15)),.3,2)
den=np.bincount(f.ravel(),weights=np.repeat(weights,3),minlength=nv)
for _ in range(25):
 centers=v[f].mean(1);off=np.sum((centers[:,None]-v[f])*filtered[:,None],axis=2)
 delta=np.zeros_like(v);np.add.at(delta,f.ravel(),(off[:,:,None]*filtered[:,None]*weights[:,None,None]).reshape(-1,3))
 proposed=v+delta/np.maximum(den[:,None],1e-15)*influence[:,None]*.65
 change=proposed-base;change*=np.minimum(1,.00065/np.maximum(np.linalg.norm(change,axis=1),1e-15))[:,None];v=base+change
# Regular barrel and gas-tube runs: fit the cylindrical surface while leaving
# collars, vents and attachment junctions untouched. This is an art-space fit.
tube_records=[]
for name,x1,x2,z1,z2 in [('BarrelForward',-.86,-.69,.078,.13),('BarrelRear',-.58,-.466,.078,.13),('GasTubeRun',-.659,-.47,.019,.068)]:
 use=(base[:,0]>x1)&(base[:,0]<x2)&(base[:,2]>z1)&(base[:,2]<z2)
 pts=base[use];yz=pts[:,1:]
 A=np.c_[2*yz,np.ones(len(yz))];q=np.linalg.lstsq(A,np.sum(yz*yz,axis=1),rcond=None)[0]
 center=q[:2];radius=np.sqrt(q[2]+center@center)
 vec=yz-center;length=np.linalg.norm(vec,axis=1);error=np.abs(length-radius)
 amount=np.clip(np.minimum(pts[:,0]-x1,x2-pts[:,0])/.012,0,1)*np.clip(1-error/.0035,0,1)*.75
 adjust=vec*(radius/np.maximum(length,1e-9)-1)[:,None]*amount[:,None]
 adjust*=np.minimum(1,.0008/np.maximum(np.linalg.norm(adjust,axis=1),1e-12))[:,None]
 v[use,1:]+=adjust
 influence[use]=np.maximum(influence[use],amount)
 tube_records.append(dict(region=name,center_yz=center.tolist(),radius=float(radius)))
# Only changed, already-smooth fans receive updated shading; hard corners retain
# source corner normals. Angle-weighted normal averaging is confined to their
# original normal direction to avoid averaging across creases.
newn,newar=fn(v);sum_n=np.zeros_like(v)
np.add.at(sum_n,f.ravel(),np.repeat(newn*np.sqrt(newar[:,None]),3,axis=0))
sum_n/=np.maximum(np.linalg.norm(sum_n,axis=1,keepdims=True),1e-15)
candidate=sum_n[f];compatible=(np.sum(candidate*old,axis=2)>.93)
blend=influence[f]*compatible*.78
n=old*(1-blend[:,:,None])+candidate*blend[:,:,None];n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-15)
np.savez_compressed(R/'faired_surface.npz',vertices=v[inv],faces=f0,uv=uv,normals=n,fairing=influence[f])
changed=np.linalg.norm(v-base,axis=1)
(R/'surface_authoring.json').write_text(json.dumps(dict(method='bounded bilateral normal projection and local cylinder fitting',source_topology_preserved=True,uv_preserved=True,changed_geometry_vertices=int((changed>1e-9).sum()),max_art_space_displacement=float(changed.max()),tube_fits=tube_records),indent=2))
print('LOCAL_SURFACE_AUTHORED',int((changed>1e-9).sum()),flush=True)
