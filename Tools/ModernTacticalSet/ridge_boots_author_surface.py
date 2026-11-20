"""Surface charts, physical UVs and moulded details for the TS01 high boot."""
import math
import numpy as np
import shapely
from scipy.interpolate import PchipInterpolator
from shapely.geometry import LineString, Polygon
from coyote_glove_author_patterns import tessellate

TAU=math.tau
SLOTS=["RB_"+s for s in ("Suede","Textile","Frame","Outsole","Lace","Lining","Hardware","Thread")]
LEVEL=[1.6,2.5,3.7,4.7,5.6,6.7,8.1,10.2,12.6,15.8,19.5,23.0,26.3,28.65]
def profile(values):
    return PchipInterpolator(LEVEL,values,extrapolate=True)
front=profile([22.0,22.58,22.70,22.42,21.52,18.55,14.15,9.25,6.05,4.13,3.27,3.2,3.49,3.51])
back=profile([-7.8,-8.07,-8.16,-8.15,-8.15,-8.04,-7.90,-7.66,-7.58,-7.71,-8.25,-8.65,-9.01,-9.1])
width=profile([5.55,5.68,5.74,5.72,5.62,5.49,5.21,4.94,4.75,4.88,5.26,5.75,6.06,6.14])

def unit(v):
    v=np.asarray(v,float)
    return v/np.maximum(1.e-12,np.linalg.norm(v,axis=-1,keepdims=True))
def ease(v):
    v=np.clip(v,0.,1.)
    return v*v*(3-2*v)
def arr(*args):
    return np.stack(np.broadcast_arrays(*args),axis=-1)
def last(t,z):
    t,z=np.broadcast_arrays(t,z)
    a,b=front(z),back(z)
    footwear=1.-ease((z-7.5)/6.2)
    cs=np.cos(t);sn=np.sin(t)
    e=.91-.20*footwear
    ly=(1.+np.sign(cs)*abs(cs)**e)*.5
    y=b+(a-b)*ly
    # The inside edge stays straighter at the ball, with a fuller big-toe tip.
    head=ease((y-9.)/12.)
    center=-.87*head*footwear+.21*np.exp(-((y-3)/3.3)**2)*footwear
    waist=np.exp(-((y-3.7)/4.55)**2)
    w=width(z)*(1.-footwear*(.13*(1.-ly)+(.17-.075*sn)*waist))
    x=center+w*np.sign(sn)*abs(sn)**e
    y-=footwear*.83*ease((y-13)/8)*np.maximum(0,sn)**1.35
    # Shallow, tapering flex folds in the bellows and Achilles above the counter.
    ripple=.076*np.sin(z*1.65-1.8*cs)*np.exp(-((z-14.4)/3.15)**2)
    return arr(x+ripple*sn,y+ripple*cs,z)
def normal(t,z):
    return unit(np.cross(last(t-.001,z)-last(t+.001,z),last(t,z+.01)-last(t,z-.01)))
def surf(t,z,h=0):
    return last(t,z)+normal(t,z)*np.asarray(h)[...,None]
def collar(t):
    # The collar drops at the Achilles; the free tongue stands above this U.
    frontness=(1.+np.cos(t))*.5
    return 24.65+2.74*frontness+.47*np.sin(t)**2
def wrap_chart(q,h):
    return surf(q[:,0]/5.5,q[:,1],h)
def side_chart(flank):
    def apply(q,h):
        y,z=q.T
        # Invert the side chart, including the asymmetric toe sweep.
        lo=np.full(len(q),.003);hi=np.full(len(q),math.pi-.003)
        for _ in range(15):
            mid=(lo+hi)*.5; v=last(flank*mid,z)[:,1]
            lo=np.where(v>y,mid,lo);hi=np.where(v>y,hi,mid)
        return surf(flank*(lo+hi)*.5,z,h)
    return apply
def poly(ctrl,r=.15):
    p=Polygon(ctrl)
    return shapely.segmentize(p.buffer(-r,join_style='round').buffer(r,quad_segs=4),.37)
def rounded_line(points,r):
    return LineString(points).buffer(r,quad_segs=5)
def strip_faces(nu,nv):
    j=(np.arange(nv-1)[:,None]*nu+np.arange(nu-1)).ravel()
    return np.vstack((np.stack((j,j+1,j+nu+1),1),np.stack((j,j+nu+1,j+nu),1)))
class Boot:
    def __init__(self):
        self.parts=[]
    def add(self,name,mat,p,f,uv,expected):
        p=np.asarray(p,float);f=np.asarray(f,int);uv=np.asarray(uv,float)
        # Produce clockwise Unreal faces and outward normals in the positive-X foot.
        c=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
        valid=np.linalg.norm(c,axis=1)>1.e-9;f=f[valid].copy();c=c[valid]
        hint=np.asarray(expected)
        if hint.ndim==2:hint=hint[f].mean(1)
        flip=(c*hint).sum(1)>0;f[flip]=f[flip,::-1]
        self.parts.append((name,SLOTS.index('RB_'+mat),p,f,uv))
    def grid(self,name,mat,fn,nu,nv,norm=None):
        u,v=np.meshgrid(np.linspace(0,1,nu),np.linspace(0,1,nv));p=fn(u,v)
        # Distances in both cloth directions remain in world centimeters.
        du=np.linalg.norm(np.diff(p,axis=1),axis=-1)
        dv=np.linalg.norm(np.diff(p,axis=0),axis=-1)
        uv=arr(np.pad(np.cumsum(du,axis=1),((0,0),(1,0))),np.pad(np.cumsum(dv,axis=0),((1,0),(0,0))))/4.
        if norm is None:norm=unit(np.cross(np.gradient(p,axis=0),np.gradient(p,axis=1)))
        else:norm=norm(u,v) if callable(norm) else np.broadcast_to(norm,p.shape)
        self.add(name,mat,p.reshape(-1,3),strip_faces(nu,nv),uv.reshape(-1,2),norm.reshape(-1,3))
    def panel(self,name,mat,outline,chart,h=.17,low=.045,step=.58,bevel=.22,crease=False):
        if crease:
            # Preserve every window edge and the two sides of its tooling
            # bevel. Bound the triangle length so the flat pattern can bend
            # around the last without creasing across an entire panel.
            core=outline.buffer(-bevel,quad_segs=3)
            xmin,zmin,xmax,zmax=outline.bounds
            x,z=np.meshgrid(np.arange(xmin,xmax,step*2),np.arange(zmin,zmax,step*2))
            cells=shapely.box(x.ravel(),z.ravel(),x.ravel()+2*step,z.ravel()+2*step)
            faces=[]
            for region in (core,outline.difference(core)):
                patches=shapely.set_precision(shapely.intersection(cells,region),.00001)
                tris=shapely.get_parts(shapely.constrained_delaunay_triangles(patches))
                faces.append(shapely.get_coordinates(tris).reshape(-1,4,2)[:,:3,:].reshape(-1,2))
            q,indices=np.unique(np.concatenate(faces).round(5),axis=0,return_inverse=True)
            f=indices.reshape(-1,3)
            loops=[np.asarray(ring.coords)[:-1] for ring in (outline.exterior,*outline.interiors)]
        else:
            q,f,loops=tessellate(outline,step)
        dist=shapely.distance(shapely.points(q),outline.boundary)
        thick=low+(h-low)*np.sin(np.clip(dist/bevel,0.,1.)*math.pi*.5)
        p=chart(q,thick);direction=unit(chart(q,.03)-chart(q,0))
        self.add(name,mat,p,f,q/4,direction)
        for k,loop in enumerate(loops):
            count=len(loop);top=chart(loop,low)
            # Wrap the mould into the leather. Its window walls meet the
            # upper at their base, including along the toe and heel curves.
            floor=chart(loop,.015 if crease else min(low-.11,.08))
            # Boundary interior is on the left for CCW rings and on the right otherwise.
            turns=shapely.is_ccw(shapely.LinearRing(loop))
            delta=np.roll(loop,-1,axis=0)-np.roll(loop,1,axis=0)
            across=unit(np.stack((delta[:,1],-delta[:,0]),1))*(1 if turns!=(k>0) else -1)
            aim=unit(chart(loop+across*.025,low)-chart(loop,low));j=np.arange(count);n=(j+1)%count
            f2=np.vstack((np.stack((j,n,n+count),1),np.stack((j,n+count,j+count),1)))
            self.add(name+'_edge'+str(k),mat,np.vstack((top,floor)),f2,np.vstack((loop,loop+[0,.10]))/4,np.vstack((aim,aim)))
    def tube(self,name,mat,path,rad=.11,ns=7,closed=False):
        path=np.asarray(path)
        if closed:path=np.vstack((path,path[:1]))
        tang=unit(np.gradient(path,axis=0))
        if closed:tang[0]=tang[-1]=unit(path[1]-path[-2])
        a=np.eye(3)[np.argmin(abs(tang[0]))]
        frame=[unit(np.cross(tang[0],a))]
        for t in tang[1:]:
            f=frame[-1]-np.dot(frame[-1],t)*t
            frame.append(unit(f) if np.linalg.norm(f)>.02 else unit(np.cross(t,np.eye(3)[np.argmin(abs(t))])))
        frame=np.asarray(frame);other=np.cross(tang,frame)
        if closed:
            phase=np.arctan2(np.dot(frame[0],other[-1]),np.dot(frame[0],frame[-1]))*np.linspace(0.,1.,len(path))
            frame=np.cos(phase)[:,None]*frame+np.sin(phase)[:,None]*other
            other=np.cross(tang,frame)
        a=np.linspace(0,TAU,ns+1);n=frame[:,None,:]*np.cos(a)[None,:,None]+other[:,None,:]*np.sin(a)[None,:,None]
        radius=np.broadcast_to(rad,len(path));p=path[:,None,:]+radius[:,None,None]*n
        d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
        uv=arr(a[None,:]*radius[:,None],d[:,None]+np.zeros_like(a))/4
        self.add(name,mat,p.reshape(-1,3),strip_faces(ns+1,len(path)),uv.reshape(-1,2),n.reshape(-1,3))
    def stitches(self,name,outline,chart,h,offset=.15):
        contracted=outline.buffer(-offset)
        for i,g in enumerate(shapely.get_parts(contracted)):
            if g.area<.1:continue
            path=LineString(g.exterior.coords);count=int(path.length/.39)
            if count<2:continue
            center=(np.arange(count)+.5)*path.length/count
            t=(center[:,None]+np.array([-.12,0,.12])[None,:]).ravel()
            xy=shapely.get_coordinates(shapely.line_interpolate_point(path,t))
            delta=shapely.get_coordinates(shapely.line_interpolate_point(path,t+.012))-xy
            norm=unit(arr(-delta[:,1],delta[:,0]))
            across=norm*np.tile([.021,.035,.021],count)[:,None]
            strip=np.stack((xy+across,xy,xy-across),1).reshape(-1,2)
            heights=np.tile([h,h+.023,h],3*count)
            j=(np.arange(count)[:,None]*9+np.array([0,1,3,4])).ravel()
            f=np.vstack((np.stack((j,j+1,j+4),1),np.stack((j,j+4,j+3),1)))
            self.add(name+str(i),'Thread',chart(strip,heights),f,strip/4,unit(chart(strip,.05)-chart(strip,0)))
            # A dark, short needle channel at either end of each stitch
            # separates tonal thread from the split-hide face.
            centers=xy[::3]; side=norm[::3]*.040;along=unit(delta[::3])*.065
            loop=np.stack((centers+along,centers+side,centers-along,centers-side),1).reshape(-1,2)
            start=np.arange(count)[:,None]*4
            faces=np.vstack((start+[0,1,2],start+[0,2,3]))
            self.add(name+'_piercing'+str(i),'Lining',chart(loop,h+.006),faces,loop/4,unit(chart(loop,.05)-chart(loop,0)))
