"""Restore M16 donor UVs and repair the balanced grip's semantic material IDs."""
import json,numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
O=Path(__file__).parent;(O/'Plans').mkdir(exist_ok=True)
def read(key):
 with (O/'Input'/(key+'.bin')).open('rb') as f:
  h=json.loads(f.readline());nv=h['vertices'];nt=h['triangles']
  p=np.fromfile(f,'<f4',nv*3).reshape(-1,3).astype(float);t=np.fromfile(f,'<i4',nt*3).reshape(-1,3);m=np.fromfile(f,'<i4',nt)
  n=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3);uv=np.fromfile(f,'<f4').reshape(h['uv_sets'],nt,3,2)
 return h,p,t,m,n,uv
S,sp,st,sm,sn,suv=read('M16_stock');D,dp,dt,dm,dn,duv=read('M4_stock')
# Exact authored transformation from M16UniversalAttachments20260920/author_models.py.
canon=np.column_stack((-sp[:,1]-4.1045,sp[:,0]+.0038,sp[:,2]-9.17))
ids=np.flatnonzero(sm!=0);centers=dp[dt].mean(axis=1)
distance,donor=cKDTree(centers).query(canon[st[ids]].mean(axis=1))
if distance.max()>.003:raise RuntimeError('Donor mismatch '+str(distance.max()))
mapped=dp[dt[donor]];target=canon[st[ids]]
err=np.linalg.norm(target[:,:,None,:]-mapped[:,None,:,:],axis=3)
permutation=err.argmin(axis=2)
if err.min(axis=2).max()>.004 or np.any(np.sort(permutation,axis=1)!=[0,1,2]):raise RuntimeError('Ambiguous donor corner matching')
newuv=np.stack([duv[layer,donor[:,None],permutation] for layer in (0,1)])
newnorm=dn[donor[:,None],permutation].astype(float)
# Transform source-space directions using the same rigid root frame.
newnorm=np.stack((newnorm[:,:,1],-newnorm[:,:,0],newnorm[:,:,2]),axis=2)
np.savez_compressed(O/'Plans/M16_stock.npz',triangles=ids,uv0=newuv[0],uv1=newuv[1],normals=newnorm)
report={'stock':{'restored_triangles':len(ids),'max_corner_fit_mm':float(err.min(axis=2).max()*10),
 'donor':'current M4 SOURCE_MODEL, full precision','target_channels':[0,1],'kept_m16_coating_channel':3}}

H,p,t,m,n,uv=read('M16_balanced')
# The source reconstruction explicitly made body below -1cm, shoulder -1..-.2cm,
# and native cap above -.2cm. Existing material IDs were shifted by one slot.
remap=np.array([1,2,0],dtype=np.int32)
for mid,(low,high) in enumerate([(-100,-.9999),(-1.0001,-.1999),(-.2001,100)]):
 z=p[t[m==mid],2]
 if z.min()<low or z.max()>high:raise RuntimeError('Grip semantic region differs')
_,first,inverse=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True)
v0=p[first];v=v0.copy();tri=inverse[t]
body=m==0;editable=np.zeros(len(v),bool);editable[tri[body].ravel()]=True;editable[tri[~body].ravel()]=False
fade=np.clip((-v0[:,2]-1.0)/.35,0,1);fade=fade*fade*(3-2*fade);mobility=fade*editable
edges=np.sort(np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]])),axis=1);owners=np.tile(np.arange(len(tri)),3)
order=np.lexsort((edges[:,1],edges[:,0]));edges=edges[order];owners=owners[order]
starts=np.r_[0,np.flatnonzero(np.any(edges[1:]!=edges[:-1],axis=1))+1];counts=np.diff(np.r_[starts,len(edges)])
mobility[edges[starts[counts!=2]].ravel()]=0
pa=starts[counts==2];fa=owners[pa];fb=owners[pa+1];keep=body[fa]&body[fb];fa,fb=fa[keep],fb[keep]
def unit(a):return a/np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-15)
def normal(v):return unit(np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]]))
guide=normal(v0);center=v0[tri].mean(axis=1);spatial=np.exp(-np.sum((center[fa]-center[fb])**2,axis=1)/(.16**2))
verts=tri.ravel();faceids=np.repeat(np.arange(len(tri)),3);count=np.bincount(verts,minlength=len(v)).clip(1)
for outer in range(2):
 nf=normal(v)
 for _ in range(6):
  cos=np.clip(np.einsum('ij,ij->i',nf[fa],nf[fb]),-1,1);w=spatial*np.exp(-(1-cos)/.075)
  w[np.einsum('ij,ij->i',guide[fa],guide[fb])<.65]=0
  total=nf.copy();den=np.ones(len(tri));np.add.at(total,fa,nf[fb]*w[:,None]);np.add.at(total,fb,nf[fa]*w[:,None]);np.add.at(den,fa,w);np.add.at(den,fb,w);nf=unit(total/den[:,None])
 for _ in range(8):
  center=v[tri].mean(axis=1);a=np.einsum('ij,ij->i',center[faceids]-v[verts],nf[faceids])[:,None]*nf[faceids]
  step=np.column_stack([np.bincount(verts,weights=a[:,j],minlength=len(v)) for j in range(3)])/count[:,None]
  d=v+step*(.65*mobility[:,None])-v0;d*=np.minimum(1,.025*mobility/np.maximum(np.linalg.norm(d,axis=1),1e-15))[:,None];v=v0+d
newpos=p+(v-v0)[inverse];moved=np.linalg.norm(newpos-p,axis=1)>1e-9
BH,bp,bt,bm,bn,buv=read('M4_balanced');donorids=np.flatnonzero(bm==0);bodyids=np.flatnonzero(m==0)
_,nearest=cKDTree(bp[bt[donorids]].mean(axis=1)).query(p[t[bodyids]].mean(axis=1));nearest=donorids[nearest]
errors=np.linalg.norm(p[t[bodyids]][:,:,None,:]-bp[bt[nearest]][:,None,:,:],axis=3);perm=errors.argmin(axis=2)
matches=(errors.min(axis=2).max(axis=1)<.03)&np.all(np.sort(perm,axis=1)==[0,1,2],axis=1)
restored=uv[0].copy();matchedids=bodyids[matches];restored[matchedids]=buv[0,nearest[matches,None],perm[matches]]
edge1=restored[:,1]-restored[:,0];edge2=restored[:,2]-restored[:,0];collapsed=(abs(edge1[:,0]*edge2[:,1]-edge1[:,1]*edge2[:,0])<1e-12)&(m==0)
# Newly clipped tiny triangles that have no exact donor triangle keep their
# atlas center and receive a local nonzero triangle instead of a zero tangent.
for i in np.flatnonzero(collapsed):
 c=restored[i].mean(axis=0);restored[i]=c+np.array([[-.00004,-.00004],[.00008,-.00004],[-.00004,.00008]])
np.savez_compressed(O/'Plans/M16_balanced.npz',positions=newpos,materials=remap[m],normal_faces=np.flatnonzero(np.any(moved[t],axis=1)),uv_triangles=bodyids,uv0=restored[bodyids])
report['balanced']={'material_remap':{'0_body':1,'1_neck':2,'2_native_cap':0},'moved_vertices':int(moved.sum()),'max_surface_displacement_mm':float(np.linalg.norm(newpos-p,axis=1).max()*10),'neck_and_native_cap_positions_changed':False,'exact_donor_uv_triangles':int(matches.sum()),'new_cut_uv_repairs':int(collapsed.sum())}
(O/'production.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Plain JSON is consumed by the UE embedded Python without external dependencies.
for key in ('M16_stock','M16_balanced'):
 data=np.load(O/'Plans'/(key+'.npz'))
 import gzip
 with gzip.open(O/'Plans'/(key+'.json.gz'),'wt',encoding='utf-8') as f:json.dump({name:data[name].tolist() for name in data.files},f)
