"""Cut a wrap neckline and sew a tool pocket against the existing artisan garment, in UE centimetres."""
from functools import lru_cache
import sys
import gzip
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d
from pattern import ROOT, SRC, normalized

sys.path.insert(0,str(ROOT/"Tools/VillageBlacksmithNPC/FinishR2/BodyOutfit"))
from cloth_surface import boundary_loops

def blend_weights(rows, coefficients):
    result={}
    for row,coef in zip(rows,coefficients):
        for bone,weight in row:result[bone]=result.get(bone,0.)+coef*weight
    pairs=sorted(((k,w) for k,w in result.items() if w>1e-6),key=lambda x:-x[1])[:8]
    total=sum(v for _,v in pairs)
    return [[int(k),round(float(v/total),7)] for k,v in pairs]

class Support:
    def __init__(self,data,name):
        first,start,last,end=data["parts"][name]
        self.p=np.array(data["positions"][first:last])
        self.f=np.array(data["triangles"][start:end])-first
        self.cloud=self.p[self.f]
        self.norm=np.array(data["normals"][start:end])
        self.tex=np.array(data["uv"][start:end])
        self.weights=data["weights"][first:last]
        centers=self.cloud.mean(axis=1)
        self.tree=cKDTree(centers)
        self.xz=cKDTree(centers[:,[0,2]])

    def sample(self,i,bary):
        nodes=self.f[i]
        return (bary@self.cloud[i],normalized(bary@self.norm[i]),
                blend_weights([self.weights[v] for v in nodes],bary))

    def closest(self,point):
        ids=self.tree.query(point,k=24)[1]
        tris=self.cloud[ids]
        q=trimesh.triangles.closest_point(tris,np.broadcast_to(point,(len(ids),3)))
        j=np.argmin(np.linalg.norm(q-point,axis=1))
        bary=trimesh.triangles.points_to_barycentric(tris[j:j+1],q[j:j+1])[0]
        bary=np.clip(bary,0,1)
        return self.sample(ids[j],bary/bary.sum())

    @lru_cache(maxsize=12000)
    def front(self,x,z):
        ids=self.xz.query([x,z],k=72)[1]
        tris=self.cloud[ids]
        a=tris[:,0,:][:,[0,2]];e=tris[:,1,:][:,[0,2]]-a;f=tris[:,2,:][:,[0,2]]-a
        q=np.array([x,z])-a
        det=e[:,0]*f[:,1]-e[:,1]*f[:,0]
        det[np.abs(det)<1e-10]=np.nan
        u=(q[:,0]*f[:,1]-q[:,1]*f[:,0])/det
        v=(e[:,0]*q[:,1]-e[:,1]*q[:,0])/det
        bary=np.column_stack([1-u-v,u,v])
        hit=np.flatnonzero((bary>=-1.e-6).all(1))
        if len(hit):
            j=hit[np.argmax((bary[hit]*tris[hit,:,1]).sum(1))]
            return self.sample(ids[j],bary[j])
        return self.closest(np.array([x,self.cloud[ids[0],:,1].max(),z]))

def sew_faces(piece,a,b,c,d,mat):
    for tri in ((a,b,c),(a,c,d)):
        p=np.array([piece.p[k] for k in tri])
        normal=np.mean([piece.n[k] for k in tri],axis=0)
        if np.dot(np.cross(p[2]-p[0],p[1]-p[0]),normal)<0:tri=tri[::-1]
        piece.face(tri,mat)

def collar_facing(piece,hem,bind_rows):
    # Connect the inside of the collar to the real weighted neck where a close camera can see under the fold.
    head=json.loads(gzip.decompress((SRC/"HeadR4/Head.json.gz").read_bytes()))
    verts=np.asarray(head["p"]);faces=np.asarray(head["tri"])[np.asarray(head["m"])==1]
    tri=verts[faces];ab=tri[:,1]-tri[:,0];ac=tri[:,2]-tri[:,0]
    rows=[]
    for p,bind in zip(hem,bind_rows):
        q=p.copy();q[2]-=.46
        center=np.array([.1,-.85,q[2]])
        radial=normalized(q-center)
        az=abs(np.arctan2(radial[0],radial[1]))
        extent=np.clip((az-.8)/.57,0,1);extent=extent*extent*(3-2*extent)
        if extent<.002:continue
        h=np.cross(radial,ac);det=np.einsum('ij,ij->i',ab,h)
        det[abs(det)<1e-9]=np.nan
        s=center-tri[:,0];u=np.einsum('ij,ij->i',s,h)/det
        c=np.cross(s,ab);v=(c@radial)/det
        dist=np.einsum('ij,ij->i',ac,c)/det
        ids=np.flatnonzero((u>=-.0001)&(v>=-.0001)&(u+v<=1.0001)&(dist>0.))
        if not len(ids):raise ValueError("Missing neck section beneath collar")
        i=ids[np.argmax(dist[ids])]
        skin=center+radial*(dist[i]-.16)
        inner_weights=blend_weights([head["w"][k] for k in faces[i]],[1.-u[i]-v[i],u[i],v[i]])
        row=[]
        for t in (0.,.32,.68,1.):
            a=t*extent
            pos=p*(1-a)+skin*a
            pos[2]-=.14+.12*np.sin(t*np.pi)
            row.append(piece.corner(pos,[0,0,1],[az*.39,t*.16],blend_weights([bind,inner_weights],[1-a,a])))
        rows.append(row)
    for a,b in zip(rows,rows[1:]):
        for i in range(3):sew_faces(piece,a[i],b[i],b[i+1],a[i+1],9)

def wrap_collar(piece,data,review_fit=False):
    shell=Support(data,"Continuous linen shirt")
    x,y,z=shell.p.T
    # The two straight cutting lines meet below the throat; the back retains the donor neckline.
    cut=z-141.7-1.48*np.abs(x-.15)-5.*np.maximum(2.15-y,0.)
    loops=boundary_loops(shell.p,shell.f)
    neck=next(loop for loop in loops if shell.p[loop,2].mean()>150)
    rim=list(shell.p[neck[cut[neck]<=0]])
    for i,face in enumerate(shell.f):
        value=cut[face]
        if value.min()>0:continue
        corners=[(shell.p[v],shell.norm[i,k],shell.tex[i,k],shell.weights[v]) for k,v in enumerate(face)]
        polygon=[]
        if value.max()<=0:polygon=corners
        else:
            for k in range(3):
                j=(k+1)%3
                if value[k]<=0:polygon.append(corners[k])
                if (value[k]<=0)!=(value[j]<=0):
                    t=value[k]/(value[k]-value[j]);a,b=corners[k],corners[j]
                    p=a[0]*(1-t)+b[0]*t
                    polygon.append((p,normalized(a[1]*(1-t)+b[1]*t),a[2]*(1-t)+b[2]*t,
                                    blend_weights([a[3],b[3]],[1-t,t])))
                    rim.append(p)
        idx=[piece.corner(*v) for v in polygon]
        for k in range(1,len(idx)-1):piece.face([idx[0],idx[k],idx[k+1]],0)

    rim=np.unique(np.round(rim,5),axis=0)
    angle=np.arctan2(rim[:,0]-.15,rim[:,1]+1.)
    theta=np.linspace(0,-2*np.pi,181)
    ring=np.column_stack([np.interp(theta,angle,rim[:,k],period=2*np.pi) for k in range(3)])
    # Extend both front ends past the V. The underlap dies under the outer lapel; the outer lapel ends beneath the sash.
    throat=ring[0]
    def front_path(target_x,target_z,count):
        path=[]
        for t in np.linspace(0,1,count)[1:]:
            u=throat[0]*(1-t)+target_x*t
            h=throat[2]*(1-t)+target_z*t
            path.append(shell.front(float(u),float(h))[0])
        return path
    start=(front_path(.5,throat[2]-.45,4) if review_fit else front_path(2.8,137.6,11))[::-1]
    end=front_path(-13.,100.85,70)
    path=np.vstack((start,ring,end))
    tangent=normalized(np.gradient(path,axis=0))
    along=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    # A closed cross-section includes the inner turn, narrow linen reveal, indigo fold and return to the shirt.
    width=np.array([-.53,-.64,-.59,-.12,.08,.18,.55,1.55,2.58,2.78,2.83,2.68])
    lift=np.array([-.04,.09,.21,.25,.23,.31,.36,.34,.23,.13,.03,-.05])
    sections=[8,8,8,8,9,9,9,9,9,9,9]
    surface=np.empty((len(path),len(width),3))
    normals=np.empty_like(surface)
    weights=[]
    for j,anchor in enumerate(path):
        _,n,_=shell.closest(anchor)
        outer=normalized(np.cross(tangent[j],n))
        layer=.16+.34*np.clip((j-len(start)-len(ring)+24)/24.,0,1)
        layer*=np.clip((len(path)-1-j)/5.,0,1)
        row=[]
        span=width.copy()
        if review_fit:
            span*=.25+.75*np.clip(j/(len(start)+3.),0,1)
            if j>=len(start)+len(ring):
                fade=np.clip((throat[2]-anchor[2])/2.1,0,1)
                span[:5]=span[:5]*(1.-.96*fade)+span[5]*.96*fade
        for k,(w,l) in enumerate(zip(span,lift)):
            q=anchor+w*outer
            foot,N,bind=shell.closest(q)
            surface[j,k]=q+N*(np.dot(foot-q,N)+layer+l)
            normals[j,k]=N
            row.append(bind)
        weights.append(row)
    # The rolled edges have their own angled normals, not a pair of coplanar painted strips.
    profile_n=normalized(np.cross(np.gradient(surface,axis=0),np.gradient(surface,axis=1)))
    mid=len(width)//2
    flip=np.where(np.sum(profile_n[:,mid]*normals[:,mid],axis=1)<0,-1.,1.)
    profile_n*=flip[:,None,None]
    ids=[[piece.corner(pos,profile_n[j,k],[along[j]/19,w/19],weights[j][k]) for k,(pos,w) in enumerate(zip(row,width))] for j,row in enumerate(surface)]
    for j in range(len(ids)-1):
        for k,mat in enumerate(sections):
            if review_fit and j>=len(start)+len(ring) and path[j,2]<throat[2]-2.1:mat=9
            sew_faces(piece,ids[j][k],ids[j+1][k],ids[j+1][k+1],ids[j][k+1],mat)
    if review_fit:
        lo=len(start);hi=lo+len(ring)
        collar_facing(piece,surface[lo:hi,1], [row[1] for row in weights[lo:hi]])

def apron_details(piece,data,review_fit=False):
    front=Support(data,"Cut leather bib and vented apron")
    def at(x,z,lift):
        p,n,w=front.front(float(x),float(z))
        return p+n*lift,w

    def binding(p):return front.front(float(p[0]),float(p[2]))[2]
    def stitched(path,slot=12,pitch=.78):
        points=np.array(path);length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
        def pos(dist):return np.array([np.interp(dist,length,points[:,k]) for k in range(3)])
        for s in np.arange(.13,length[-1]-.42,pitch):
            piece.tube([pos(s),pos(s+.42)],.052,slot,binding,6)

    # A two-channel slip pocket on the wearer's right. Both panels are seated on the draped front, including when it bends.
    def pocket(u,t):
        half=4.45+.64*np.sin(t*np.pi/2)-.53*(1-t)**8
        x=-7.6+u*half+.30*t
        z=77.8+13.65*t+.68*(abs(u)**3)*(1-t)-.35*(1-u*u)*t
        fullness=.17+(1-abs(u)**3)*np.sin(min(1.,t/.22)*np.pi/2)*(1.22+.36*t)
        return at(x,z,fullness)[0]
    U=np.linspace(-1,1,23);T=np.linspace(0,1,28)
    outer=np.array([[pocket(u,t) for u in U] for t in T])
    piece.grid(outer,binding,3,(.58,.83))
    # Turn the mouth back inside, and close both side gussets and the pocket bottom to the actual apron.
    lip=outer[-1]
    inside=np.array([q-.22*front.front(float(q[0]),float(q[2]))[1]-[0,0,.31] for q in lip])
    piece.grid([inside,(lip+inside)*.5+[0,.04,.19],lip],binding,3,(.58,.065))
    for edge in [outer[:,0],outer[:,-1],outer[0],np.array([pocket(.08,t) for t in T])]:
        foot=np.array([at(q[0],q[2],.07)[0] for q in edge])
        piece.grid([foot,edge],binding,3,(.62,.06))
    for u in (-.90,.90,.08):
        trail=[pocket(u,t)+[0,.07,0] for t in np.linspace(.05,.97,26)]
        stitched(trail)
    stitched([pocket(u,.055)+[0,.07,0] for u in U])
    stitched([pocket(u,.965)+[0,.07,0] for u in U])
    def rigid_tool(x,top,bottom,profile,slot,flat=False):
        # Rigid tools take one binding at the mouth; their buried ends slide behind the pocket face.
        mouth=91.2
        p0,n,bind=front.front(x,mouth)
        center=p0+np.array([0,.64 if review_fit else .84,0])
        lo=front.front(x,mouth-(3.4 if review_fit else 2.))[0];hi=front.front(x,mouth+(0.15 if review_fit else 2.))[0]
        axis=hi-lo;axis/=axis[2]
        if flat:
            contour=np.array([[-.86,-1],[.86,-1],[1,-.72],[1,.72],[.86,1],[-.86,1],[-1,.72],[-1,-.72],[-.86,-1]])
        else:
            a=np.linspace(0,2*np.pi,17);contour=np.column_stack([np.cos(a),np.sin(a)])
        Udir=normalized(np.cross(n,axis))
        Vdir=normalized(np.cross(axis,Udir))
        rows=[]
        for t,w,d in profile:
            pos=center+axis*(bottom+(top-bottom)*t-mouth)
            rows.append(pos+contour[:,:1]*w*Udir+contour[:,1:]*d*Vdir)
        same=lambda _:bind
        piece.grid(rows,same,slot,(.35,.68),radial=True)
        for row,normal in ((rows[0],-normalized(axis)),(rows[-1],normalized(axis))):
            ids=[piece.corner(q,normal,[float(i)/len(row),0],bind) for i,q in enumerate(row[:-1])]
            for i in range(1,len(ids)-1):
                face=[ids[0],ids[i],ids[i+1]]
                if np.dot(np.cross(row[i+1]-row[0],row[i]-row[0]),normal)<0:face.reverse()
                piece.face(face,slot)
        return lambda xx,depth,z:center+axis*(z-mouth)+Udir*xx+Vdir*depth
    ruler=rigid_tool(-9.9,97.9,88.0 if review_fit else 86.,[(0,.84,.19),(.98,.84,.19),(1,.76,.16)],10,True)
    for k in range(8):
        z=92.3+k*.71
        piece.tube([ruler(-.66,.20,z),ruler(.22 if k%4==0 else -.12,.20,z)],.026,11,
                   lambda _:front.front(-9.9,91.2)[2],5)
    rigid_tool(-5.6,96.7,87.,[(0,.15,.15),(.36,.23,.23),(.49,.42,.43),(.67,.65,.66),(.90,.72,.73),(.98,.55,.55),(1,.34,.34)],10)
    rigid_tool(-5.6,92.1,91.5,[(0,.40,.40),(.12,.45,.45),(.88,.45,.45),(1,.40,.40)],6)
    # A shallow peened head closes each stress point at the pocket mouth.
    for u in (-.84,.84):
        c=pocket(u,.87);_,n,bind=front.front(float(c[0]),float(c[2]))
        axis=normalized(np.cross(n,[0,0,1.]));up=normalized(np.cross(axis,n));a=np.linspace(0,2*np.pi,15)
        rows=[c+n*rise+rad*(np.cos(a)[:,None]*axis+np.sin(a)[:,None]*up) for rise,rad in [(.025,.27),(.075,.27),(.13,.18),(.145,.018)]]
        piece.grid(rows,lambda _:bind,6,(1,1),radial=True)

    # A narrow saddle stitch follows the existing curved skirt edges up to the waistband.
    for side in (-1,1):
        edge=[]
        for z in np.linspace(56.5,99.6,75):
            q=front.p[np.abs(front.p[:,2]-z)<.86]
            if len(q):
                x=(q[:,0].max()-.70 if side==1 else q[:,0].min()+.70)
                edge.append(at(x,z,.065)[0])
        if len(edge)>1:stitched(edge,pitch=.91)
