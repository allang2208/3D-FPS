"""Pattern pieces for the MCDU-derived patrol shirt, laid out in centimetres."""
import math
import numpy as np
from scipy.spatial import cKDTree
import shapely
from shapely.geometry import Polygon,LineString
from coyote_glove_author_patterns import tessellate

SLOTS=['PS_Jersey','PS_Ripstop','PS_Reinforcement','PS_Loop','PS_Binding','PS_Thread','PS_Hardware']

def unit(v):
    v=np.asarray(v,float)
    return v/np.maximum(1e-12,np.linalg.norm(v,axis=-1,keepdims=True))

def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)

def polygon(points,r=.17):
    return shapely.segmentize(Polygon(points).buffer(-r,join_style='mitre').buffer(r,quad_segs=4),.50)

class Skin:
    def __init__(self,mesh,count):
        self.p=np.array(mesh['positions']);self.f=np.array(mesh['triangles'][:count])
        self.points=self.p[self.f]
        self.normals=np.array(mesh['normals'][:count])
        self.tree=cKDTree(self.points.mean(1))
        self.bones={b['name']:np.array(b['position']) for b in mesh['bones']}
        self.weights=mesh['weights']

    def hit(self,starts,rays,radius):
        rays=unit(rays);starts=np.asarray(starts)
        ends=starts+rays*np.broadcast_to(radius,len(starts))[:,None]
        fi=np.zeros(len(starts),int);bary=np.zeros((len(starts),3));pending=np.arange(len(starts))
        for k in (32,112,352):
            if not len(pending):break
            _,ix=self.tree.query(ends[pending],k=k)
            tri=self.points[ix];u=tri[:,:,1]-tri[:,:,0];v=tri[:,:,2]-tri[:,:,0]
            dr=rays[pending,None,:];s=starts[pending,None,:]-tri[:,:,0]
            h=np.cross(dr,v);den=np.einsum('ijk,ijk->ij',u,h)
            inv=1./np.where(abs(den)>1.e-8,den,np.inf)
            a=np.sum(s*h,axis=2)*inv;q=np.cross(s,u)
            b=np.sum(q*dr,axis=2)*inv;dist=np.sum(v*q,axis=2)*inv
            valid=(dist>.03)&(dist<24)&(a>=-1e-6)&(b>=-1e-6)&(a+b<=1.000001)
            choice=np.argmin(np.where(valid,dist,1.e10),axis=1);rr=np.flatnonzero(valid.any(1))
            selected=pending[rr];idx=choice[rr]
            fi[selected]=ix[rr,idx];bary[selected]=np.column_stack((1-a[rr,idx]-b[rr,idx],a[rr,idx],b[rr,idx]))
            pending=pending[~valid.any(1)]
        if len(pending):
            # Above the open shoulder/cuff boundary, attach to the closest
            # edge rather than extrapolating through the open sleeve.
            _,ii=self.tree.query(ends[pending]);fi[pending]=ii
            co=np.linalg.norm(self.points[ii]-ends[pending,None,:],axis=2)
            bary[pending,np.argmin(co,axis=1)]=1
        p=np.einsum('ijk,ij->ik',self.points[fi],bary)
        n=unit(np.einsum('ijk,ij->ik',self.normals[fi],bary))
        return p,n,fi,bary

class Arm:
    def __init__(self,skin,side):
        self.skin=skin;self.sign=1 if side=='l' else -1
        self.start,self.elbow,self.hand=[skin.bones[k+'_'+side] for k in ['upperarm','lowerarm','hand']]
        self.a,self.b=unit(self.elbow-self.start),unit(self.hand-self.elbow)
        self.upper=np.linalg.norm(self.elbow-self.start);self.length=self.upper+np.linalg.norm(self.hand-self.elbow)

    def __call__(self,q):
        s=q[:,1];k=np.clip(s,0,self.upper)
        center=self.start+self.a*k[:,None]+self.b*np.maximum(0,s-self.upper)[:,None]
        mix=smooth((s-self.upper+3.3)/6.6)[:,None]
        tangent=unit(self.a*(1-mix)+self.b*mix)
        out=np.array([self.sign,0.,0.])
        out=unit(out-np.sum(out*tangent,axis=1)[:,None]*tangent)
        along=unit(np.cross(tangent,out))*(-self.sign)
        angle=q[:,0]/5.35
        radial=out*np.cos(angle[:,None])+along*np.sin(angle[:,None])
        radius=np.interp(s,[0,self.upper*.53,self.upper,self.length-8,self.length],[6.8,5.6,4.9,3.9,3.2])
        return self.skin.hit(center,radial,radius)

class Cut:
    def __init__(self,d,skin):
        self.d=d;self.skin=skin

    def added(self,p,n,fi,coeff,f,uv,slot,name):
        p=np.asarray(p);dest=self.d;offset=len(dest['positions']);f=np.asarray(f,int).copy()
        face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
        flip=np.sum(face*n[f].mean(1),axis=1)<0;f[flip]=f[flip,::-1]
        face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
        good=np.linalg.norm(face,axis=1)>1.e-8;f=f[good];face=face[good]
        smooth_n=np.zeros_like(p)
        for j in range(3):np.add.at(smooth_n,f[:,j],face)
        smooth_n=unit(smooth_n)
        joints=self.skin.f[fi];weights=[]
        for ids,bb in zip(joints,coeff):
            w={}
            for i,weight in zip(ids,bb):
                for bi,bw in self.skin.weights[i]:w[bi]=w.get(bi,0.)+bw*max(0.,weight)
            ww=sorted(((i,v) for i,v in w.items() if v>.00003),key=lambda a:-a[1])[:8]
            total=sum(v for _,v in ww);weights.append([[i,round(v/total,7)] for i,v in ww])
        start=len(dest['triangles']);dest['positions'].extend(p.round(6).tolist());dest['weights']+=weights
        dest['triangles'].extend((f+offset).tolist());dest['normals'].extend(smooth_n[f].round(6).tolist())
        dest['uv'].extend(np.asarray(uv)[f].round(6).tolist());dest['triangle_materials'].extend([SLOTS.index(slot)]*len(f))
        dest['parts'][name]=[start,len(dest['triangles'])]

    def panel(self,key,chart,poly,slot,height,lip=.25,wall=.035,underlay=None):
        q,f,loops=tessellate(poly,.55)
        dist=shapely.distance(shapely.points(q),poly.boundary)
        h=height(q) if callable(height) else np.full(len(q),height)
        datum=underlay(q) if underlay else 0.
        h=datum+wall+(h-datum-wall)*smooth(dist/lip)
        ring=loops[0];count=len(ring);a=np.arange(count);b=np.roll(a,-1)
        q1=np.vstack((q,ring));p,n,fi,bary=chart(q1)
        inner=underlay(ring)+.005 if underlay else np.full(count,.005)
        p+=n*np.r_[h,inner][:,None];end=a+len(q)
        self.added(p,n,fi,bary,np.vstack([f,np.column_stack((a,b,np.roll(end,-1))),np.column_stack((a,np.roll(end,-1),end))]),q1/8,slot,key)
        return poly

    def line(self,key,chart,coords,width,height,slot='PS_Thread',pitch=None):
        ln=LineString(coords)
        if ln.length<.12:return
        if pitch:
            count=max(1,int(ln.length/pitch));mid=(np.arange(count)+.5)*ln.length/count
            ts=(mid[:,None]+np.array([-.13,0,.13])[None,:]).ravel()
            breaks=np.arange(len(ts)-1)%3!=2
        else:
            ts=np.linspace(0,ln.length,max(2,round(ln.length/.29)));breaks=np.ones(len(ts)-1,bool)
        xy=shapely.get_coordinates(shapely.line_interpolate_point(ln,ts))
        tang=shapely.get_coordinates(shapely.line_interpolate_point(ln,np.minimum(ln.length,ts+.025)))-shapely.get_coordinates(shapely.line_interpolate_point(ln,np.maximum(0,ts-.025)))
        cross=unit(np.stack((-tang[:,1],tang[:,0]),axis=1))
        q=(xy[:,None,:]+np.array([-width,0,width])[None,:,None]*cross[:,None,:]).reshape(-1,2)
        p,n,fi,w=chart(q);h=height(q) if callable(height) else height
        p+=n*(h+np.tile([0,min(.062,width*.67),0],len(xy)))[:,None]
        j=(np.flatnonzero(breaks)[:,None]*3+np.array([0,1])).ravel()
        f=np.vstack((np.stack((j,j+1,j+4),1),np.stack((j,j+4,j+3),1)))
        self.added(p,n,fi,w,f,q/8,slot,key)

def sleeve(cut,side):
    arm=Arm(cut.skin,side);prefix=side+'_'
    def panel(name,poly,mat,h,lip=.25):
        return cut.panel(prefix+name,arm,poly,mat,h,lip)
    def stitch(name,poly,h,offset=.17):
        outline=poly.buffer(-offset).exterior
        cut.line(prefix+name,arm,outline.coords,.042,h,pitch=.40)
    # Slightly pitched pocket front opening, binding and compressed bellows.
    u=arm.upper
    pocket=polygon([(-4.5,5.9),(-2.8,4.8),(3.2,6.7),(4.15,8.4),(3.05,19.4),(1.9,20.6),(-4.3,18.9),(-5.0,17.5)],.40)
    def pleat(q):
        y=q[:,1];x=q[:,0];return .26+.34*np.exp(-((x+3.6)/1.08)**2)*smooth((y-6)/3)*smooth((20-y)/3)
    panel('angled_bicep_pocket',pocket,'PS_Ripstop',pleat)
    stitch('bicep_pocket_stitch',pocket,lambda q:pleat(q)+.024)
    patch=polygon([(-3.35,8.),(1.18,9.16),(.60,16.77),(-3.63,15.72)],.28)
    # The loop field is sewn onto the pocket including its bellows. Its
    # folded perimeter follows the pocket face all the way to the seam.
    cut.panel(prefix+'loop_field',arm,patch,'PS_Loop',lambda q:pleat(q)+.14,.16,.065,pleat)
    stitch('loop_perimeter',patch,lambda q:pleat(q)+.159,.14)
    rail=np.array([[2.58,7.69],[2.99,8.70],[2.09,17.15],[1.78,18.80]])
    cut.line(prefix+'reverse_zip_tape',arm,rail,.39,.33,'PS_Binding')
    cut.line(prefix+'zip_coil',arm,rail,.105,.395,'PS_Hardware',pitch=.28)
    slider=polygon([(2.28,8.44),(2.94,8.46),(3.02,9.39),(2.45,9.50)],.08)
    panel('zip_slider',slider,'PS_Hardware',.55,.08)
    cut.line(prefix+'zip_pull',arm,[(2.7,9.20),(2.34,9.83),(2.23,10.70),(2.6,10.76),(2.87,9.87),(2.72,9.42)],.09,.55,'PS_Binding')
    # Soft two-sided articulated elbow facing. Darts terminate at the hinge
    # and bend with its underlying forearm and upper-arm influences.
    joint=u
    elbow=polygon([(-8.4,joint-5.3),(-5.8,joint-6.8),(-.85,joint-5.9),(1.3,joint-3.4),
                   (1.55,joint+.5),(.70,joint+5.8),(-1.46,joint+8.9),(-5.75,joint+8.6),
                   (-8.25,joint+5.8),(-9.67,joint+1.4),(-9.72,joint-2.4)],.48)
    def elbow_height(q):
        x,s=q.T;rel=s-joint
        ridge=np.exp(-((rel-3.50+.27*(x+4))/.49)**2)+.82*np.exp(-((rel-5.22+.22*(x+4))/.52)**2)
        return .17+.38*ridge*smooth((x+9)/2.4)*smooth((1.4-x)/2.5)+.14*np.exp(-((rel+.4)/3.8)**2)
    panel('articulated_elbow_sleeve',elbow,'PS_Reinforcement',elbow_height,.32)
    stitch('elbow_recessed_seam',elbow,lambda q:elbow_height(q)+.015,.24)
    for i,coords in enumerate([[(-8.1,joint-3.9),(-5.8,joint-2.2),(-4.15,joint-1.7)],
                               [(.67,joint+.6),(-.65,joint-.6),(-2.19,joint-1.0)]]):
        cut.line(prefix+'elbow_dart_'+str(i),arm,coords,.055,lambda q:elbow_height(q)+.025,'PS_Thread')
    wrist=arm.length
    # The tab ends short of the original rim, leaving the established glove
    # overlap and skin insert free to follow the native wrist.
    tab=polygon([(-5.10,wrist-5.68),(2.25,wrist-5.32),(3.79,wrist-4.48),(3.55,wrist-3.33),
                 (2.43,wrist-2.91),(-4.92,wrist-3.48)],.28)
    landing=polygon([(-1.24,wrist-5.78),(5.15,wrist-5.27),(4.97,wrist-2.52),(-1.42,wrist-2.96)],.25)
    panel('cuff_loop_landing',landing,'PS_Loop',.15,.14)
    panel('cuff_adjustment_tab',tab,'PS_Ripstop',.35,.20)
    stitch('cuff_tab_stitch',tab,.37)
    cut.line(prefix+'bar_tack',arm,[(-4.47,wrist-5.24),(-4.61,wrist-3.73)],.092,.365,'PS_Thread',pitch=.24)
