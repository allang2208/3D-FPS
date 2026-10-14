"""Repair the local loft correspondence, retaining original lower grip geometry."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import isotonic_regression,minimize_scalar
O=Path(__file__).parent;C=json.loads((O/'Input/current.json').read_text());report={}
factory=np.array(list(json.loads((O/'Input/factory.json').read_text())['factory']['vertices'].values()))*np.array([100,-100,100])
factorytop=factory[factory[:,2]>.5999,:2];factoryhull=factorytop[ConvexHull(factorytop).vertices]
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-15)
def ease(v):v=np.clip(v,0,1);return v*v*(3-2*v)
for kind in C:
 with (O/'Input'/(kind+'.bin')).open('rb') as f:
  h=json.loads(f.readline());nv,nt=h['vertices'],h['triangles'];source=np.fromfile(f,'<f4',nv*3).reshape(-1,3).astype(float);tri=np.fromfile(f,'<i4',nt*3).reshape(-1,3);np.fromfile(f,'<i4',nt);normal=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3).astype(float);uv=np.fromfile(f,'<f4',nt*6).reshape(-1,3,2)
 _,ix,iv=np.unique(np.round(source,5),axis=0,return_index=True,return_inverse=True);p=source[ix];T=iv[tri]
 mask=np.zeros(len(p));np.maximum.at(mask,T.ravel(),uv[:,:,0].ravel());levels=np.unique(np.round(mask,4))
 sides=(uv[:,:,0].max(1)>1e-5)&(uv[:,:,0].min(1)<.9999)
 st=T[sides];edges=np.unique(np.sort(np.r_[st[:,[0,1]],st[:,[1,2]],st[:,[2,0]]],1),axis=0)
 rings=[]
 for level in levels:
  on=np.isclose(mask,level,atol=1e-5);ee=edges[on[edges[:,0]]&on[edges[:,1]]];adj={}
  for a,b in ee:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
  if not adj or any(len(v)!=2 for v in adj.values()):raise RuntimeError('Not a simple neck ring '+kind+' '+str(level))
  start=min(adj);cur=start;prev=None;ring=[]
  while True:
   ring.append(cur);nxt=next(v for v in adj[cur] if v!=prev);prev,cur=cur,nxt
   if cur==start:break
  if len(ring)!=len(adj):raise RuntimeError('Multiple loft ring components')
  rr=np.array(ring);xy=p[rr,:2];area=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1))
  if area<0:rr=rr[::-1]
  if rings:
   previous=rings[-1];links={tuple(e) for e in edges};choices=[]
   for shift in range(len(rr)):
    ids=np.roll(rr,shift)
    connected=sum(tuple(sorted((int(a),int(b)))) in links for a,b in zip(previous,ids))
    if connected==len(rr):choices.append((float(np.mean(np.linalg.norm(p[ids,:2]-p[previous,:2],axis=1))),ids))
   if not choices:raise RuntimeError('Loft correspondence missing')
   rr=min(choices,key=lambda q:q[0])[1]
  rings.append(rr)
 rings=np.array(rings);base=p[rings[0],:2];oldtop=p[rings[-1],:2];count=len(base)
 ds=np.linalg.norm(np.roll(base,-1,axis=0)-base,axis=1);s=np.r_[0,np.cumsum(ds[:-1])];per=ds.sum()
 # Arc-length smoothing avoids transferring tiny cut-edge dents into needle-like
 # narrow triangle strips. It affects only the new neck above the fixed cut.
 distance=np.abs(s[:,None]-s[None,:]);distance=np.minimum(distance,per-distance)
 kernel=np.exp(-.5*(distance/.30)**2)*((ds+np.roll(ds,1))*.5)[None,:];kernel/=kernel.sum(1,keepdims=True)
 smoothbase=kernel@base
 hull=factoryhull;hd=np.linalg.norm(np.roll(hull,-1,axis=0)-hull,axis=1);hs=np.r_[0,np.cumsum(hd)];hp=hs[-1]
 def contour(q):
  q=np.mod(q,hp);idx=np.minimum(np.searchsorted(hs,q,side='right')-1,len(hull)-1);u=(q-hs[idx])/hd[idx]
  return hull[idx]*(1-u[:,None])+hull[(idx+1)%len(hull)]*u[:,None]
 # Recover the existing contour parameter, then remove only local reversals.
 # Global arc redistribution would shift vertices far along a concave source.
 edge=np.roll(hull,-1,axis=0)-hull
 fraction=np.clip(np.sum((oldtop[:,None,:]-hull[None,:,:])*edge[None,:,:],axis=2)/(hd*hd)[None,:],0,1)
 projected=hull[None,:,:]+fraction[:,:,None]*edge[None,:,:]
 closest=np.argmin(np.linalg.norm(projected-oldtop[:,None,:],axis=2),axis=1)
 raw=hs[closest]+fraction[np.arange(count),closest]*hd[closest]
 raw=np.unwrap(raw/hp*2*np.pi)*hp/(2*np.pi)
 print('CONTOUR_PARAMETER',kind,'perimeter',hp,'span',raw[-1]-raw[0],'range',raw.min(),raw.max(),'max_jump',np.max(np.abs(np.diff(raw))),flush=True)
 if raw[-1]-raw[0]<hp*.8:
  # Balanced's legacy radial projection doubles back and never encircles its
  # mounting top. Re-seat this ring on the full, actual factory footprint.
  def cost(offset):return np.mean(np.sum((contour(s/per*hp+offset)-oldtop)**2,axis=1))
  fits=[minimize_scalar(cost,bounds=(i*hp/12,(i+1)*hp/12),method='bounded') for i in range(12)]
  offset=min(fits,key=lambda v:v.fun).x;iso=s/per*hp+offset
 else:iso=isotonic_regression(raw,increasing=True).x
 fallback=np.mod(iso*.97+(iso[0]+s/per*hp)*.03,hp);param=fallback.copy()
 # Keep the actual mounting corners in the vertex ring, not an inset chord.
 used=set()
 for corner in hs[:-1]:
  dist=np.abs(param-corner);dist=np.minimum(dist,hp-dist)
  idx=next(int(v) for v in np.argsort(dist) if int(v) not in used);param[idx]=corner;used.add(idx)
 # Retain every actual bevel corner while preserving circular vertex order.
 order=np.argsort(fallback);param[order]=np.sort(param)
 top=contour(param)
 height=float(np.median(p[rings[-1],2])-np.median(p[rings[0],2]));z0=float(np.median(p[rings[0],2]))
 slope=(p[rings[1],:2]-base)/(height*levels[1]);slope=kernel@slope;slope*=np.minimum(1,.55/np.maximum(np.linalg.norm(slope,axis=1),1e-9))[:,None]
 out=p.copy()
 for ids,t in zip(rings[1:],levels[1:]):
  b=base*(1-ease(t/.22))+smoothbase*ease(t/.22);blend=ease(t)
  out[ids,:2]=b*(1-blend)+top*blend+slope*height*t*(1-t)**2
  out[ids,2]=z0+height*t
 updated=source+(out-p)[iv]
 # Parameter-space normals are independent of irregular triangle area/density.
 surface=out[rings];tangent=np.empty_like(surface)
 for j in range(len(levels)):
  line=surface[j];length=np.maximum(np.linalg.norm(np.roll(line,-1,axis=0)-line,axis=1),1e-9)
  fw=(np.roll(line,-1,axis=0)-line)/length[:,None];bw=(line-np.roll(line,1,axis=0))/np.roll(length,1)[:,None]
  tangent[j]=unit(fw+bw)
 longitudinal=np.gradient(surface,levels,axis=0);smoothnormal=unit(np.cross(tangent,longitudinal))
 normals_by_vertex=np.zeros_like(p);normals_by_vertex[rings.ravel()]=smoothnormal.reshape(-1,3)
 newnorm=normal.copy();local=normals_by_vertex[T[sides]];old=normal[sides]
 if np.median(np.sum(local*old,axis=2))<0:local=-local
 strength=ease(uv[sides,:,0]/.13);newnorm[sides]=unit(old*(1-strength[:,:,None])+local*strength[:,:,None])
 cap=uv[:,:,0].min(1)>.9999;newnorm[cap]=np.array([0.,0.,1.])
 oldpoints=source[tri];oldcross=np.cross(oldpoints[:,1]-oldpoints[:,0],oldpoints[:,2]-oldpoints[:,0])
 winding_sign=float(np.sign(np.median(np.sum(oldcross*normal.mean(1),axis=1))))
 points=updated[tri];cross=np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0])
 flipped=np.flatnonzero((sides|cap)&(np.sum(cross*newnorm.mean(1),axis=1)*winding_sign<-1e-12))
 moved=np.flatnonzero(np.linalg.norm(updated-source,axis=1)>1e-7);changed=np.flatnonzero(np.max(np.linalg.norm(newnorm-normal,axis=2),axis=1)>1e-6)
 changed=np.union1d(changed,flipped)
 head={'key':kind,'source_sha256':h['sha256'],'vertices':nv,'triangles':nt,'moved':len(moved),'normal_triangles':len(changed),'orientation_flip_ids':flipped.tolist()}
 with (O/'Plans'/(kind+'.bin')).open('wb') as f:
  f.write((json.dumps(head)+'\n').encode())
  for a in (moved.astype('<i4'),updated[moved].astype('<f4'),changed.astype('<i4'),newnorm[changed].astype('<f4')):a.tofile(f)
 lower=mask[iv]<1e-5
 report[kind]={**{k:v for k,v in head.items() if k!='orientation_flip_ids'},'orientation_flipped_triangles':len(flipped),'native_winding_sign':winding_sign,'method':'Fixed source cut, monotonic factory-footprint contour loft, arc-length smoothing, parameter-space normals',
  'cut_z_cm':z0,'ring_vertices':count,'ring_count':len(levels),'max_move_mm':float(np.linalg.norm(updated-source,axis=1).max()*10),
  'lower_positions_unchanged':bool(np.array_equal(updated[lower],source[lower])),'lower_normals_unchanged':bool(np.array_equal(newnorm[~(sides|cap)],normal[~(sides|cap)])),
  'top_height_cm':float(surface[-1,:,2].mean()),'factory_footprint_area_ratio_before':float(ConvexHull(oldtop).volume/ConvexHull(hull).volume),'factory_footprint_area_ratio_after':float(ConvexHull(top).volume/ConvexHull(hull).volume),
  'connectivity_changed':False,'triangle_orientation_changed':bool(len(flipped)),'material_changed':False,'uv_values_changed':False}
 print('JUNCTION_AUTHORED',kind,json.dumps(report[kind]),flush=True)
(O/'production.json').write_text(json.dumps(report,indent=2))
