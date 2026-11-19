"""Reconstruct a continuous fitted cloth surface from the smith's bound body and donor shirt."""
import numpy as np
from numba import njit
from scipy.ndimage import distance_transform_edt,gaussian_filter,binary_closing,gaussian_filter1d
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes

def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)
def row_normals(p,tri):
    s=np.zeros_like(p)
    q=p[tri];fn=np.cross(q[:,2]-q[:,0],q[:,1]-q[:,0])
    for k in (0,1,2):np.add.at(s,tri[:,k],fn)
    return unit(s)
def clip(p,tri,fn):
    dist=fn(p);idx=dist>=0
    old=np.flatnonzero(idx)
    ids=np.empty(len(p),int);ids[old]=np.arange(len(old))
    v=list(p[old]);out=list(ids[tri[idx[tri].all(axis=1)]])
    lut={}
    for face in tri[idx[tri].any(axis=1)&~idx[tri].all(axis=1)]:
        poly=[]
        for i,j in zip(face,np.roll(face,-1)):
            if idx[i]:poly.append(ids[i])
            if idx[i]!=idx[j]:
                key=tuple(sorted((i,j)))
                if key not in lut:
                    fac=dist[i]/(dist[i]-dist[j]);lut[key]=len(v);v.append(p[i]+(p[j]-p[i])*fac)
                poly.append(lut[key])
        for k in range(1,len(poly)-1):out.append([poly[0],poly[k],poly[k+1]])
    return np.asarray(v),np.asarray(out)
class Bind:
    def __init__(self,p,weights):
        self.tree=cKDTree(p);self.w=weights
    def __call__(self,points):
        ds,ids=self.tree.query(points,k=4);a=1/np.maximum(.06,ds)**2;a/=np.sum(a,axis=1)[:,None];res=[]
        for ii,ff in zip(ids,a):
            row={}
            for vid,fac in zip(ii,ff):
                for j,w in self.w[vid]:row[j]=row.get(j,0)+w*fac
            ww=sorted(row.items(),key=lambda kv:-kv[1])[:8];s=sum(a for _,a in ww)
            res.append([[int(j),round(float(w/s),7)] for j,w in ww if w/s>1e-6])
        return res

@njit
def depth_raster(tris,nx,nz):
    low=np.full((nx,nz),np.inf);high=np.full((nx,nz),-np.inf)
    for v in tris:
        a,b,c=v[0],v[1],v[2]
        x1,z1=b[0]-a[0],b[2]-a[2];x2,z2=c[0]-a[0],c[2]-a[2];den=x1*z2-z1*x2
        if abs(den)<1e-9:continue
        for i in range(max(0,int(np.ceil(min(a[0],b[0],c[0])))),min(nx-1,int(np.floor(max(a[0],b[0],c[0]))))+1):
            for k in range(max(0,int(np.ceil(min(a[2],b[2],c[2])))),min(nz-1,int(np.floor(max(a[2],b[2],c[2]))))+1):
                u=((i-a[0])*z2-(k-a[2])*x2)/den;r=(x1*(k-a[2])-z1*(i-a[0]))/den
                if u<-.00001 or r<-.00001 or u+r>1.00001:continue
                y=a[1]+u*(b[1]-a[1])+r*(c[1]-a[1])
                low[i,k]=min(low[i,k],y);high[i,k]=max(high[i,k],y)
    return low,high

def garment_cloud(body,donor,shoulders,elbows,hands):
    pitch=.58;start=np.array([-46.,-23.,93.])
    sizes=np.ceil((np.array([46.,26.,163.])-start)/pitch).astype(int)+1
    # The base shirt's upper sleeve and neck can be open; the body contributes the actual interior.
    triangles=np.concatenate([body,donor])
    lo,hi=depth_raster((triangles-start)/pitch,sizes[0],sizes[2])
    yy=np.arange(sizes[1])[None,:,None]
    vol=(yy>=lo[:,None,:])&(yy<=hi[:,None,:]);vol=binary_closing(vol,iterations=1)
    sdf=(distance_transform_edt(vol)-distance_transform_edt(~vol))*pitch
    sdf=gaussian_filter(sdf,1.28)
    indices=np.indices(sizes,sparse=True);x,y,z=[start[i]+indices[i]*pitch for i in range(3)]
    xa=abs(x);phi=np.arctan2(y,np.maximum(xa-16,0.1))
    # Remove the short-sleeve donor's thick factory hem while preserving the
    # underlying upper arm and rolled-cuff volumes.
    arm_zone=smooth(16,24,xa)*smooth(116,123,z)*(1-smooth(138,146,z))
    sdf+=arm_zone*(gaussian_filter(sdf,4.0)-sdf)
    offset=.46+.38*np.exp(-((z-121)/17)**2)
    # A handful of broad worn-in compression folds and cutting ease around the waist/underarm.
    offset=offset+.60*np.exp(-((z-(107.1+.15*xa+.09*y))/1.55)**2)-.17*np.exp(-((z-(109+.15*xa+.10*y))/1.4)**2)
    offset=offset+.45*np.exp(-((z-(113.0-.23*xa-.08*y))/1.4)**2)*smooth(5,13,xa)
    offset=offset+.50*np.exp(-((z-(129.5+.43*(xa-14)-.19*y))/2.6)**2)*smooth(8,19,xa)
    for side in (-1,1):
        sh,el,hand=shoulders[side],elbows[side],hands[side]
        upper=unit(el-sh);lower=unit(hand-el)
        s=(x-el[0])*upper[0]+(y-el[1])*upper[1]+(z-el[2])*upper[2]
        az=(y-el[1])*.62+side*(x-el[0])*.34
        arm=smooth(16,24,side*x)*smooth(-17,-8,s)
        offset=offset+arm*(.52+.47*np.exp(-((s+2.9+.30*az)/1.25)**2)
                            +.65*np.exp(-((s+.3-.24*az)/1.35)**2)
                            +.46*np.exp(-((s-2.4+.13*az)/1.30)**2))
    # Iso-surface before pattern cutting lets the neckline, armscyes and upper torso share their topology.
    field=sdf+offset
    p,f,_,_=marching_cubes(field,0,spacing=(pitch,)*3,allow_degenerate=False,gradient_direction='descent')
    p=p+start
    # Normals point towards lower field values in world space, UE index order is clockwise.
    q=p[f];face=np.cross(q[:,2]-q[:,0],q[:,1]-q[:,0])
    front=(q.mean(1)[:,1]>10)&(abs(q.mean(1)[:,0])<7)
    if np.median(face[front,1])<0:f=f[:,::-1]
    def neck_height(q):
        a=np.arctan2(q[:,0],q[:,1]+.55)
        return 152.0-.86*np.cos(a)-2.1*np.exp(-(a/.28)**2)
    p,f=clip(p,f,lambda q:neck_height(q)-q[:,2])
    p,f=clip(p,f,lambda q:q[:,2]-99.3)
    for side in (-1,1):
        axis=unit(hands[side]-elbows[side]);el=elbows[side]
        p,f=clip(p,f,lambda q:np.maximum(19-side*q[:,0],6.6-(q-el)@axis))
    return p,f

def boundary_loops(p,tri):
    edge=np.sort(np.vstack([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]]),axis=1)
    edges,counts=np.unique(edge,axis=0,return_counts=True);edges=edges[counts==1]
    adj={}
    for i,j in edges:adj.setdefault(i,[]).append(j);adj.setdefault(j,[]).append(i)
    seen=set();loops=[]
    for start in adj:
        if start in seen:continue
        loop=[];j=start
        while j not in seen:
            seen.add(j);loop.append(j);fresh=[k for k in adj[j] if k not in seen]
            if not fresh:break
            j=fresh[0]
        if len(loop)>10:loops.append(np.array(loop))
    return loops

def grid_tris(m,n,cycle=False,reverse=False):
    f=[]
    for j in range(m-1):
        for i in range(n if cycle else n-1):
            k=(i+1)%n;a=j*n+i;b=j*n+k;c=(j+1)*n+k;d=(j+1)*n+i
            f.extend([(a,b,c),(a,c,d)])
    a=np.asarray(f)
    return a[:,::-1] if reverse else a

def rays_at_x(cloud,x):
    s=cloud[:,:,0]-x
    k=(s.min(axis=1)<=0)&(s.max(axis=1)>0)
    v=cloud[k];s=s[k];i,j=np.where((s>0)!=(np.roll(s,-1,axis=1)>0));a=(j+1)%3
    xyz=v[i,j]-(s[i,j]/(s[i,a]-s[i,j]))[:,None]*(v[i,a]-v[i,j])
    return xyz[:,1:].reshape(-1,2,2)
def ray_dist(segments,origin,direction):
    rel=segments-origin;cross=rel@np.array([-direction[1],direction[0]])
    hit=(cross[:,0]<0)!=(cross[:,1]<0);v=rel[hit];c=cross[hit]
    distance=(v[:,0]+(v[:,1]-v[:,0])*(-c[:,0]/(c[:,1]-c[:,0]))[:,None])@direction
    return distance[distance>0]
