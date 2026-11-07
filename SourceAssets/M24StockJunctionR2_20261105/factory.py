"""Use the live host's rear-seat corners as the replacement wrist, in native UE centimetres."""
import json,gzip
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
O=Path(__file__).resolve().parent
parts=json.load(gzip.open(O/'Inputs/action-triangles.json.gz','rt'))
don=json.loads((O/'Inputs/factory-seat.json').read_text())
cut=10.4; out=[]; cap_edges=[]
def deform(v):
    x,y,z=v; t=np.clip((-y-5.2)/3.,0,1);w=t*t*(3-2*t)
    dz=np.logaddexp(0.,(z-9.30)*5.)/5.
    return np.array([x*(1-.08*w),y,z-w*dz])
def clip(row):
    v=np.array(row['pos']);n=np.array(row['norm']);uv=np.array(row['uv']).transpose(1,0,2).reshape(3,-1)
    data=np.column_stack((v,n,uv)); result=[];ends=[]
    for a,b in zip(data,np.roll(data,-1,axis=0)):
        keep=a[1]>=-cut
        if keep:result.append(a)
        if keep!=(b[1]>=-cut):
            t=(-cut-a[1])/(b[1]-a[1]);c=a+(b-a)*t;result.append(c);ends.append(c)
    if len(ends)==2:cap_edges.append(ends)
    return np.array(result)
def append(face):
    vs=face[:,:3];ns=face[:,3:6].copy()
    for i,v in enumerate(vs):
        if v[1]>=-5.2:continue
        jac=np.stack([(deform(v+e)-deform(v-e))/.0002 for e in np.eye(3)*.0001],axis=1)
        ns[i]=np.linalg.solve(jac.T,ns[i])
    ns/=np.linalg.norm(ns,axis=1)[:,None]
    out.append({'pos':[deform(v).tolist() for v in vs],'norm':ns.tolist(),'uv':face[:,6:].reshape(3,-1,2).transpose(1,0,2).tolist()})
for row in don:
    poly=clip(row)
    for k in range(1,len(poly)-1):append(poly[[0,k,k+1]])
# A terminal edge is internal to the bedding. Tessellate its actual cross-section,
# preserving the channel cut-out rather than bridging it with a convex hull.
from shapely.geometry import LineString
from shapely.ops import polygonize,triangulate,unary_union
lines=[LineString([tuple(np.round(p[[0,2]],5)) for p in pair]) for pair in cap_edges]
loops=list(polygonize(unary_union(lines)))
if not loops:raise RuntimeError('Unclosed factory bedding section')
for loop in loops:
    for tri in triangulate(loop):
        if not loop.covers(tri):continue
        xz=np.array(tri.exterior.coords)[:3];p=np.column_stack((xz[:,0],np.full(3,-cut),xz[:,1]))
        if np.cross(p[1]-p[0],p[2]-p[0])[1]>0:p=p[::-1]
        out.append(dict(pos=[deform(a).tolist() for a in p],norm=[[0,-1,0]]*3,uv=[(p[:,[0,2]]*.16).tolist()]*4))
rm=[]
for positions,faces,materials in parts:
    v=np.array(positions);f=np.array(faces);_,key=np.unique(v.round(4),axis=0,return_inverse=True)
    tr=key[f];i=tr.ravel();j=tr[:,[1,2,0]].ravel();groups=connected_components(coo_matrix((np.ones(len(i)),(i,j)),shape=(key.max()+1,)*2),directed=False)[1][tr[:,0]]
    selected=[]
    for g in np.unique(groups):
        ids=np.flatnonzero(groups==g);verts=v[f[ids]].reshape(-1,3)
        lo,hi=verts.min(0),verts.max(0)
        if hi[1]>-2.55 and lo[1]>=-10.401 and hi[1]<-1.99 and lo[2]>4.4 and hi[2]<9.46 and np.max(np.abs(verts[:,0]))<2.36:
            selected.extend(ids.tolist())
    if not selected:raise RuntimeError('Original transition was not found')
    rm.append([{'i':i,'c':v[f[i]].mean(0).tolist()} for i in selected])
old=np.array(json.load(open(O.parent/'M24FactoryStockSeam20261105/source_seam.json'))['boundary']).reshape(-1,3)*[100,-100,100]
dist=cKDTree(np.array([t['pos'] for t in out]).reshape(-1,3)).query(old)[0].max()
if dist>.002:raise RuntimeError('Lost factory stock boundary')
(O/'Exports/factory-patch.json').write_text(json.dumps({'remove':rm,'insert':out,'max_cut_error_cm':dist},separators=(',',':')))
print('Factory wrist',len(out),'triangles; original removed',list(map(len,rm)),'max seam distance mm',dist*10)
