"""Native-bound soft leather trousers, built from approved Concept02.

Blender background production only. No UE asset writes or preview renders.
"""
import copy,gc,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerLeatherPants20261021';ITEM='ue_leather_pants'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import unit,normals,norm_weights,blend_weights,boundary,vertex,face,read,write
SLOTS=['WalnutLeather','ReinforcedLeather','OliveTwill','DarkLining','WaxedThread','AgedSteel']
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
def bary(p,tri):
    a,b=tri[1]-tri[0],tri[2]-tri[0];q=p-tri[0];aa,ab,bb=a@a,a@b,b@b;den=max(aa*bb-ab*ab,1e-12)
    v=(bb*(q@a)-ab*(q@b))/den;w=(aa*(q@b)-ab*(q@a))/den;c=np.maximum([1-v-w,v,w],0);return c/max(sum(c),1e-12)
def center(z,sign):
    h=[11.8,20,30,40,47.35,58,67,80]
    return np.array([sign*np.interp(z,h,[14.8,14.2,13.5,12.6,12.04,11.2,10.5,9.8]),np.interp(z,h,[-2.5,-2.,-1.2,-.4,.8,1.7,2.3,2.6]),z])
def angle(p):
    sign=1 if p[0]>=0 else -1;c=center(p[2],sign);return math.atan2(sign*(p[0]-c[0]),p[1]-c[1])
def fabric(p):
    z=p[2];t=angle(p);back=math.atan2(math.sin(t-math.pi),math.cos(t-math.pi));inner=math.atan2(math.sin(t+math.pi/2),math.cos(t+math.pi/2))
    knee=1-((z-47.5)/6.4)**2-(back/.82)**2
    gusset=1-((z-74.5)/13.0)**2-(inner/.70)**2
    return max(knee,gusset)
def base():
    src=read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json');bone_names={b['index']:b['name'] for b in src['bones']};ps=[];ws=[];fs=[];lookup={};first=0
    for part in src['parts']:
        if part['name'] in ('Leather_WaistAndSeat','Leather_Leg_L','Leather_Leg_R'):
            for tri in src['triangles'][first:first+part['triangles']]:
                row=[]
                for i in tri:
                    p=src['positions'][i];key=tuple(np.round(p,5))
                    if key not in lookup:lookup[key]=len(ps);ps.append(p);ws.append({bone_names[b]:w for b,w in src['weights'][i]})
                    row.append(lookup[key])
                fs.append(row)
        first+=part['triangles']
    # Real deformation resolution: subdivide the continuous shell once; all
    # midpoint weights are interpolated from the native, fitted garment.
    edge={};out=[]
    for a,b,c in fs:
        mids=[]
        for i,j in ((a,b),(b,c),(c,a)):
            key=tuple(sorted((i,j)))
            if key not in edge:edge[key]=len(ps);ps.append(((np.array(ps[i])+ps[j])*.5).tolist());ws.append(blend_weights(ws[i],ws[j],.5))
            mids.append(edge[key])
        ab,bc,ca=mids;out.extend([[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]])
    ps=np.array(ps);fs=np.array(out);edges=np.unique(np.sort(np.concatenate((fs[:,[0,1]],fs[:,[1,2]],fs[:,[2,0]])),axis=1),axis=0)
    rows=np.r_[edges[:,0],edges[:,1]];cols=np.r_[edges[:,1],edges[:,0]];count=np.bincount(rows,minlength=len(ps))
    fixed=np.zeros(len(ps),bool)
    for a,b in boundary(fs):fixed[a]=fixed[b]=True
    def mean(v):
        result=np.zeros_like(v);np.add.at(result,rows,v[cols]);return result/np.maximum(count,1)[:,None]
    weight=(1-smooth((ps[:,2]-94)/5))*.25;weight[fixed]=0
    for _ in range(7):ps+=weight[:,None]*(mean(ps)-ps);ps-=.96*weight[:,None]*(mean(ps)-ps)
    ns=normals(ps,fs)
    for i,p in enumerate(ps):
        z=p[2];t=angle(p);s=1 if p[0]>=0 else -1;c=center(z,s)
        if z<75:
            # Tailored lower leg with sufficient thigh ease; keep the calibrated waist.
            taper=.075*(1-smooth((z-25)/23));ps[i,:2]=c[:2]+(p[:2]-c[:2])*(1-taper)
        knee=math.exp(-((z-48)/8.0)**2);ankle=math.exp(-((z-18)/6.8)**2)
        front=max(0,math.cos(t))**2;side=abs(math.sin(t))
        fold=.07*knee*math.sin((z-45)*.8+1.6*math.sin(t))+.16*ankle*math.sin(z*1.4+2*t)
        # Authored diagonal tension folds radiate from hip/crotch instead of
        # regular horizontal sine bands covering the entire leather surface.
        for height,amplitude,width in ((83.0,.32,.75),(78.7,.23,.85),(72.4,.18,1.05)):
            q=z-(height-3.2*math.sin(t)+.25*s*math.sin(t*2))
            fold+=front*amplitude*(math.exp(-(q/width)**2)-.42*math.exp(-((q+.95)/(width*.72))**2))
        for height in (40.5,55.6):
            q=z-height-1.0*math.sin(t*2);fold+=side*.15*math.exp(-(q/.8)**2)
        fold*=float(1-smooth((z-91)/5));ps[i]+=ns[i]*fold
    # Six large tailoring charts, solved on the final shape and scaled to 8 cm.
    me=bpy.data.meshes.new('ContinuousTailoring');me.from_pydata([(x,-y,z) for x,y,z in ps],[],fs.tolist());me.update();ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
    groups=[]
    for tri in fs:
        p=ps[tri].mean(0);c=center(p[2],1 if p[0]>=0 else -1)
        groups.append((0 if p[2]>80 else 1 if p[0]>=0 else 2, p[1]>(.8 if p[2]>80 else c[1])))
    edge_groups={}
    for tri,grp in zip(fs,groups):
        for a,b in zip(tri,np.roll(tri,-1)):edge_groups.setdefault(tuple(sorted((int(a),int(b)))),set()).add(grp)
    for e in me.edges:e.use_seam=len(edge_groups[tuple(sorted(e.vertices))])>1
    me.uv_layers.new(name='Physical8cm');bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.unwrap(method='ANGLE_BASED',margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    layer=me.uv_layers.active;uv=np.array([[[layer.data[i].uv.x,1-layer.data[i].uv.y] for i in f.loop_indices] for f in me.polygons])
    sys.path.insert(0,str(P/'Tools/ModularOutfit'));from author_chainmail_shirt import mail_uv
    uv,charts=mail_uv(ps,fs,uv);uv=np.array(uv)*25/8;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(me)
    return src,ps,fs,ws,uv

class Tailor:
    def __init__(self,src,ps,fs,ws,uv):
        self.ps,self.fs,self.ws,self.uv=ps,fs,ws,uv;self.ns=normals(ps,fs)
        self.tree=BVHTree.FromPolygons([Vector(p) for p in ps],fs.tolist(),all_triangles=True)
        self.d=dict(profile='Jason',binding_source=src['source'],source=src['source'],skeleton=src['skeleton'],bones={b['name']:{k:v for k,v in b.items() if k!='name'} for b in src['bones']},positions=[],triangles=[],weights=[],uv=[],normals=[],triangle_materials=[],colors=[],parts=[],material_slots=SLOTS,contract='Approved LeatherPants Concept02: continuous fitted Jason native shell; shared layer weights; articulated supple leather knees; olive twill mobility gusset; sewn real pockets, belt and cuff closures; centimetres')
    def sample(self,origin,direction,distance=65):
        hit,_,fi,_=self.tree.ray_cast(Vector(origin),Vector(direction),distance)
        if hit is None:raise RuntimeError('Tailoring ray missed '+str((origin,direction)))
        tri=self.fs[fi];bc=bary(np.array(hit),self.ps[tri]);n=unit(bc@self.ns[tri]);w=norm_weights({k:sum(self.ws[v].get(k,0)*a for v,a in zip(tri,bc)) for k in set().union(*(self.ws[v] for v in tri))})
        return np.array(hit),n,w
    def front(self,x,z):return self.sample([x,40,z],[0,-1,0])
    def rear(self,x,z):return self.sample([x,-40,z],[0,1,0])
    def side(self,y,z,sign):return self.sample([sign*50,y,z],[-sign,0,0])
    def leg(self,t,z,sign):
        # Start INSIDE this leg. A ray from 28 cm outside the medial side starts
        # inside/across the other leg and incorrectly stitches the two cuffs.
        c=center(z,sign);dr=np.array([sign*math.sin(t),math.cos(t),0]);return self.sample(c,dr,24)
    def waist(self,t,z):
        c=np.array([0,.8,z]);dr=np.array([math.sin(t),math.cos(t),0]);return self.sample(c+dr*35,-dr,35)
    def append(self,name,ps,fs,ws,uv,slot,ns=None,colors=None):
        d=self.d;start=len(d['positions']);first=len(d['triangles']);ps=np.array(ps);fs=np.array(fs,int)
        d['positions'].extend(ps.tolist());d['weights'].extend(copy.deepcopy(ws));d['colors'].extend(colors if colors is not None else [[1,1,1,1] for _ in ps])
        slots=[slot]*len(fs) if isinstance(slot,int) else slot
        if ns is None:ns=normals(ps,fs)[fs]
        d['triangles'].extend((fs+start).tolist());d['triangle_materials'].extend(slots);d['normals'].extend(np.array(ns).tolist());d['uv'].extend(np.array(uv).tolist())
        d['parts'].append(dict(name=name,first_vertex=start,vertices=len(ps),first_triangle=first,triangles=len(fs),material=slot if isinstance(slot,int) else 'mixed'))
    def shell(self):
        # Clip fabric boundaries exactly within triangles; paired inner shell is
        # derived afterwards so the panels cannot open under different weights.
        ps=[];ws=[];ns=[];fs=[];uv=[];slots=[];lookup={}
        def put(p,n,w):
            key=tuple(np.round(p,7))
            if key not in lookup:lookup[key]=len(ps);ps.append(p);ns.append(n);ws.append(w)
            return lookup[key]
        for fi,tri in enumerate(self.fs):
            values=[fabric(p) for p in self.ps[tri]]
            for cloth in ((False,True) if min(values)<0<max(values) else (min(values)>=0,)):
                poly=[(np.eye(3)[i],values[i]) for i in range(3)];clipped=[]
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    ia=a[1]>=0 if cloth else a[1]<=0;ib=b[1]>=0 if cloth else b[1]<=0
                    if ia:clipped.append(a[0])
                    if ia!=ib:clipped.append(a[0]+a[1]/(a[1]-b[1])*(b[0]-a[0]))
                for j in range(1,len(clipped)-1):
                    row=[];tex=[]
                    for bc in (clipped[0],clipped[j],clipped[j+1]):
                        w=norm_weights({k:sum(self.ws[v].get(k,0)*a for v,a in zip(tri,bc)) for k in set().union(*(self.ws[v] for v in tri))});row.append(put(bc@self.ps[tri],unit(bc@self.ns[tri]),w));tex.append(bc@self.uv[fi])
                    if len(set(row))==3:fs.append(row);uv.append(tex);slots.append(2 if cloth else 0)
        ps=np.array(ps);fs=np.array(fs);ns=np.array(ns);uv=np.array(uv);n=len(ps);coords=np.vstack((ps,ps-ns*.12));weights=ws+copy.deepcopy(ws)
        triangles=np.vstack((fs,fs[:,::-1]+n));tex=np.concatenate((uv,uv[:,::-1]));face_ns=np.concatenate((ns[fs],-ns[fs[:,::-1]]));mats=slots+[3]*len(fs)
        self.append('ContinuousLeatherAndMobilityPanels',coords,triangles,weights,tex,mats,face_ns)
        for a,b in boundary(fs):
            points=coords[[b,a,a+n,b+n]];faces=[[0,1,2],[0,2,3]];l=np.linalg.norm(ps[a]-ps[b])/8;tex=np.array([[0,0],[l,0],[l,.12/8],[0,.12/8]])
            self.append('TurnedShellEdge',points,faces,[ws[b],ws[a],ws[a],ws[b]],tex[faces],1)
        self.outer_count=len(fs)
    def tube(self,name,path,weights,radius,slot,closed=False,sides=6):
        path=np.array(path);n=len(path);p=[];w=[];fs=[];uv=[];vns=[];face_ns=[];arcs=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))];previous_a=None
        for i,point in enumerate(path):
            tangent=unit(path[(i+1)%n]-path[(i-1)%n]) if closed else unit(path[min(i+1,n-1)]-path[max(i-1,0)])
            a=unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.85 else [0,1,0])) if previous_a is None else unit(previous_a-tangent*(previous_a@tangent))
            b=np.cross(tangent,a);previous_a=a
            for angle in np.linspace(0,math.tau,sides,endpoint=False):
                normal=a*math.cos(angle)+b*math.sin(angle);p.append(point+radius*normal);vns.append(normal);w.append(weights[i])
        for i in range(n if closed else n-1):
            nxt=(i+1)%n;length=np.linalg.norm(path[nxt]-path[i]);s0=arcs[i]/8;s1=(arcs[i]+length)/8
            for j in range(sides):
                ids=[i*sides+j,i*sides+(j+1)%sides,nxt*sides+(j+1)%sides,nxt*sides+j];tex=[[s0,j/sides],[s0,(j+1)/sides],[s1,(j+1)/sides],[s1,j/sides]]
                for order in ((0,1,2),(0,2,3)):
                    tri=[ids[k] for k in order];tp=np.array([p[k] for k in tri]);rad=tp.mean(0)-(path[i]+path[nxt])*.5;order=list(order)
                    if np.cross(tp[1]-tp[0],tp[2]-tp[0])@rad>0:order.reverse()
                    fs.append([ids[k] for k in order]);uv.append([tex[k] for k in order]);face_ns.append([vns[ids[k]] for k in order])
        if not closed:
            for end in (0,n-1):
                ci=len(p);p.append(path[end]);w.append(weights[end]);out=unit(path[end]-path[1 if end==0 else n-2])
                for j in range(sides):
                    tri=[ci,end*sides+j,end*sides+(j+1)%sides];tp=np.array([p[k] for k in tri]);tex=[[.5,.5],[0,0],[1,0]]
                    if np.cross(tp[1]-tp[0],tp[2]-tp[0])@out>0:tri.reverse();tex.reverse()
                    fs.append(tri);uv.append(tex);face_ns.append([out,out,out])
        self.append(name,p,fs,w,uv,slot,ns=face_ns)
    def stitches(self,name,samples,closed=False,pitch=.42):
        p=np.array([s[0] for s in samples]);n=np.array([s[1] for s in samples]);w=[s[2] for s in samples]
        if closed:p=np.r_[p,p[:1]];n=np.r_[n,n[:1]];w=w+w[:1]
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        for k,distance in enumerate(np.arange(pitch*.5,arc[-1]-.15,pitch)):
            points=[];weights=[]
            for t in (0,.5,1):
                a=distance+(t-.5)*.25;i=min(len(p)-2,max(0,np.searchsorted(arc,a)-1));f=(a-arc[i])/max(arc[i+1]-arc[i],1e-8)
                points.append(p[i]*(1-f)+p[i+1]*f+unit(n[i]*(1-f)+n[i+1]*f)*(.005+.025*math.sin(math.pi*t)));weights.append(blend_weights(w[i],w[i+1],f))
            self.tube(name+'_'+str(k),points,weights,.018,4,sides=4)
    def patch(self,name,outline,project,slot=1,rise=.19,stitch=True):
        outline=np.array(outline);curve=[]
        for i,b in enumerate(outline):
            a=outline[(i-1)%len(outline)];c=outline[(i+1)%len(outline)];e=outline[(i+2)%len(outline)]
            for t in np.linspace(0,1,6,endpoint=False):curve.append((2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*(c-a)*.34+(-2*t**3+3*t*t)*c+(t**3-t*t)*(e-b)*.34)
        curve=np.array(curve);middle=curve.mean(0);N=len(curve);points=[];ws=[];ns=[];tex=[];radii=np.r_[0.,np.linspace(.12,1,9)]
        for row,r in enumerate(radii):
            for q in ([middle] if row==0 else [middle+(q-middle)*r for q in curve]):
                p,n,w=project(*q);offset=.045+rise*(1-.83*smooth((r-.80)/.20));points.append(p+n*offset);ns.append(n);ws.append(w);tex.append(q)
        fs=[]
        for i in range(N):fs.append([0,1+i,1+(i+1)%N])
        for row in range(len(radii)-2):
            for i in range(N):
                a=1+row*N+i;b=1+row*N+(i+1)%N;fs.extend([[a,b,b+N],[a,b+N,a+N]])
        p=np.array(points);ns=np.array(ns);fs=np.array(fs)
        for i,tri in enumerate(fs):
            if np.cross(p[tri[1]]-p[tri[0]],p[tri[2]]-p[tri[0]])@ns[tri].mean(0)>0:fs[i]=tri[::-1]
        # Local metric charts use panel arclength rather than angular radians.
        tex=np.array(tex);scale=[1,1]
        for axis in range(2):
            lo=int(np.argmin(tex[:,axis]));hi=int(np.argmax(tex[:,axis]));scale[axis]=np.linalg.norm(p[hi]-p[lo])/max(tex[hi,axis]-tex[lo,axis],1e-8)
        tex=tex*np.array(scale)/8;count=len(p);bottom=p-ns*.055;coords=np.vstack((p,bottom));faces=np.vstack((fs,fs[:,::-1]+count));uv=np.concatenate((tex[fs],tex[fs[:,::-1]]));colors=[]
        for _ in range(2):
            for r in radii:colors.extend([[1+.055*smooth((r-.90)/.10)]*3+[1-.08*smooth((r-.90)/.10)]]*(1 if r==0 else N))
        self.append(name,coords,faces,ws+copy.deepcopy(ws),uv,slot,colors=colors)
        ring=np.arange(1+(len(radii)-2)*N,len(p))
        for a,b in zip(ring,np.roll(ring,-1)):
            pp=coords[[a,b,b+count,a+count]];tri=[[0,1,2],[0,2,3]];l=np.linalg.norm(p[a]-p[b])/8;uv=np.array([[0,0],[l,0],[l,.055/8],[0,.055/8]])
            # Match shell orientation to the front panel's directed boundary.
            outward=unit((pp[:2].mean(0)-p[0])-ns[a]*((pp[:2].mean(0)-p[0])@ns[a]))
            if np.cross(pp[1]-pp[0],pp[2]-pp[0])@outward>0:tri=[[0,2,1],[0,3,2]]
            self.append(name+'_TurnedEdge',pp,tri,[ws[a],ws[b],ws[b],ws[a]],uv[tri],slot)
        if stitch:
            for r in (.90,.965):
                samples=[]
                for q in curve:
                    p,n,w=project(*(middle+(q-middle)*r));samples.append((p+n*(.045+rise*(1-.83*smooth((r-.80)/.20))+.015),n,w))
                self.stitches(name+'_SaddleStitch',samples,True)

    def band(self,name,fn,nu,nv,rise=.16,slot=1,closed=False,stitch=True):
        points=[];ns=[];ws=[];N=nu if closed else nu+1
        for row in range(nv+1):
            for col in range(N):
                p,n,w=fn(col/nu,row/nv);points.append(p+n*rise);ns.append(n);ws.append(w)
        points=np.array(points);ns=np.array(ns);tex=np.zeros((nv+1,N,2));grid=points.reshape(nv+1,N,3)
        for row in range(nv+1):tex[row,1:,0]=np.cumsum(np.linalg.norm(np.diff(grid[row],axis=0),axis=1))/8
        for row in range(1,nv+1):tex[row,:,1]=tex[row-1,:,1]+np.linalg.norm(grid[row]-grid[row-1],axis=1)/8
        fs=[];uv=[]
        for row in range(nv):
            for col in range(nu):
                nxt=(col+1)%N;ids=[row*N+col,row*N+nxt,(row+1)*N+nxt,(row+1)*N+col]
                tt=np.array([tex[row,col],tex[row,nxt],tex[row+1,nxt],tex[row+1,col]])
                if closed and nxt==0:
                    tt[1,0]=tt[0,0]+np.linalg.norm(grid[row,col]-grid[row,nxt])/8;tt[2,0]=tt[3,0]+np.linalg.norm(grid[row+1,col]-grid[row+1,nxt])/8
                for order in ((0,1,2),(0,2,3)):
                    order=list(order);tri=[ids[k] for k in order];p=points[tri]
                    if np.cross(p[1]-p[0],p[2]-p[0])@ns[tri].mean(0)>0:order.reverse()
                    fs.append([ids[k] for k in order]);uv.append([tt[k] for k in order])
        fs=np.array(fs);uv=np.array(uv);count=len(points);p=np.vstack((points,points-ns*.09))
        self.append(name,p,np.vstack((fs,fs[:,::-1]+count)),ws+copy.deepcopy(ws),np.concatenate((uv,uv[:,::-1])),slot)
        for a,b in boundary(fs):
            pp=p[[b,a,a+count,b+count]];tri=[[0,1,2],[0,2,3]];l=np.linalg.norm(points[a]-points[b])/8;tt=np.array([[0,0],[l,0],[l,.09/8],[0,.09/8]])
            self.append(name+'_Edge',pp,tri,[ws[b],ws[a],ws[a],ws[b]],tt[tri],slot)
        if stitch:
            for v in (.12,.88):
                samples=[]
                for u in np.linspace(0,1,nu*2,endpoint=not closed):
                    p,n,w=fn(u,v);samples.append((p+n*(rise+.02),n,w))
                self.stitches(name+'_DoubleSeam',samples,closed)

    def stud(self,name,sample,radius=.28,rise=.16):
        p,n,w=sample;p=p+n*rise;a=unit(np.cross(n,[0,0,1] if abs(n[2])<.85 else [0,1,0]));b=np.cross(n,a)
        ps=[p+n*radius*.32];ws=[w];fs=[];uv=[];N=16;rows=5
        for i in range(1,rows+1):
            theta=i/rows*math.pi/2
            for j in range(N):
                t=j/N*math.tau;ps.append(p+radius*math.sin(theta)*(a*math.cos(t)+b*math.sin(t))+n*radius*.32*math.cos(theta));ws.append(w)
        for j in range(N):fs.append([0,1+j,1+(j+1)%N])
        for i in range(rows-1):
            for j in range(N):
                a0=1+i*N+j;b0=1+i*N+(j+1)%N;fs.extend([[a0,b0,b0+N],[a0,b0+N,a0+N]])
        for i,tri in enumerate(fs):
            pp=np.array([ps[v] for v in tri]);tex=[[(ps[v]-p)@a/(radius*2)+.5,(ps[v]-p)@b/(radius*2)+.5] for v in tri]
            if np.cross(pp[1]-pp[0],pp[2]-pp[0])@n>0:fs[i]=tri[::-1];tex=tex[::-1]
            uv.append(tex)
        self.append(name,ps,fs,ws,uv,5)

def details(t):
    # Every layer is fitted to the same garment surface and inherits its weights.
    t.band('CurvedWaistband',lambda u,v:t.waist(u*math.tau,96.15+3.8*v),128,8,.12,closed=True)
    t.band('SuppleLeatherBelt',lambda u,v:t.waist(.045+u*(math.tau-.09),97.08+2.25*v),152,5,.31)
    for k,theta in enumerate((.33,1.2,2.1,math.pi,4.18,5.08,5.94)):
        t.band('SewnBeltLoop_'+str(k),lambda u,v,theta=theta:t.waist(theta+(u-.5)*.085,96.20+3.6*v),5,10,.53,0,stitch=False)
    p,n,w=t.front(0,98.2);p=p+n*.63;h=np.array([1,0,0]);v=unit(np.cross(h,n));width=4.4;height=3.05;rr=.35;contour=[]
    for cx,cy,start in ((width/2-rr,height/2-rr,0),(-width/2+rr,height/2-rr,90),(-width/2+rr,-height/2+rr,180),(width/2-rr,-height/2+rr,270)):
        for angle in np.linspace(start,start+90,8,endpoint=False):
            theta=math.radians(angle);contour.append(p+h*(cx+rr*math.cos(theta))+v*(cy+rr*math.sin(theta)))
    t.tube('RoundedSteelBuckle',contour,[w]*len(contour),.115,5,True,8)
    t.tube('BuckleCrossbar',[p-v*1.30,p+v*1.30],[w,w],.085,5,sides=8)
    t.tube('BuckleTongue',[p+n*.11-h*.12,p+n*.11+h*2.1],[w,w],.075,5,sides=8)
    t.band('BeltKeeper',lambda u,v:t.waist(-.22+(u-.5)*.06,96.98+2.45*v),4,8,.52,stitch=False)
    t.patch('FlyFacing',[[-.6,95.9],[1.4,95.9],[1.3,84.5],[.1,83.2],[-.6,85.5]],t.front,rise=.10)
    for sign in (1,-1):
        label='L' if sign==1 else 'R'
        leg=lambda a,z,sign=sign:t.leg(a,z,sign)
        front=lambda x,z,sign=sign:t.front(sign*x,z)
        rear=lambda x,z,sign=sign:t.rear(sign*x,z)
        side=lambda y,z,sign=sign:t.side(y,z,sign)
        # Low profile inset front mouth, leather welts and dark pocket interior.
        def pocket(u,v,sign=sign):
            x=6.7+8.1*u+(v-.5)*.60;z=95.4-10.2*u+(v-.5)*.50;return t.front(sign*x,z)
        t.band('InsetPocketInterior_'+label,pocket,30,4,.055,3,stitch=False)
        for flank in (-1,1):
            t.band('RolledPocketWelt_'+label+str(flank),lambda u,v,flank=flank:pocket(u,.5+flank*.68+(v-.5)*.68),30,4,.19,0)
        for u in (.035,.965):
            samples=[pocket(u+(v-.5)*.045,v) for v in np.linspace(0,1,8)];samples=[(p+n*.23,n,w) for p,n,w in samples];t.stitches('PocketBarTack_'+label,samples,pitch=.11)
        # Sculpted soft knee cap and an independent shallow curved upper band.
        t.patch('ArticulatedKnee_'+label,[[-.62,54.9],[.55,54.9],[.70,51.8],[.56,45.7],[.30,40.0],[-.23,39.2],[-.56,43.2],[-.72,50.4]],leg,rise=.26)
        t.band('KneeUpperDart_'+label,lambda u,v:leg(-.70+1.35*u,56.45+.85*math.sin(math.pi*u)+(v-.5)*.95),44,5,.13)
        # Saddle-shaped seat reinforcement follows the pelvis and flexes with it.
        t.patch('SeatReinforcement_'+label,[[2.0,91.4],[9.8,91.6],[15.1,87.5],[14.2,82.0],[10.8,78.5],[5.7,76.8],[2.1,82.8]],rear,rise=.12)
        t.band('RearWeltRecess_'+label,lambda u,v:rear(4.0+8.5*u,92.8+(v-.5)*.52),28,3,.055,3,stitch=False)
        t.patch('RearPocketFlap_'+label,[[3.8,94.5],[12.7,94.1],[12.5,92.2],[8.2,90.9],[3.9,92.1]],rear,rise=.23)
        t.stud('RearPocketSnap_'+label,rear(8.2,92.1),.28,.32)
        # Narrow stitched tool pocket on the OUTER thigh, never crossing crotch.
        t.patch('LowProfileSidePocket_'+label,[[-3.0,79.2],[3.3,79.2],[3.0,65.1],[-1.8,64.3],[-3.0,65.7]],side,rise=.47)
        t.band('SidePocketOpening_'+label,lambda u,v:side(-2.7+5.7*u,78.3+(v-.5)*.56),20,3,.56,3,stitch=False)
        t.patch('SidePocketTopWelt_'+label,[[-3.1,80.0],[3.4,80.0],[3.3,78.7],[-3.1,78.7]],side,rise=.58)
        # Tailoring seams taper into the knee; no loose straps or rigid pads.
        for offset in (-.025,.025):
            samples=[leg(.82+.48*(z-57)/26+offset,z) for z in np.linspace(57,79.8,90)]
            t.stitches('CurvedThighSeam_'+label,[(p+n*.035,n,w) for p,n,w in samples])
        for a in (math.pi/2,-math.pi/2):
            samples=[leg(a,z) for z in np.linspace(14.5,64,100)];t.stitches('LegConstructionSeam_'+label,[(p+n*.035,n,w) for p,n,w in samples])
        # Small side cuff adjuster, designed to tuck into the fitted tall boots.
        t.band('TurnedAnkleHem_'+label,lambda u,v:leg(u*math.tau,11.95+2.1*v),96,5,.09,closed=True)
        t.patch('CuffAdjustmentTab_'+label,[[1.18,12.3],[1.98,12.3],[2.01,14.2],[1.20,14.2]],leg,rise=.22)
        t.stud('CuffAdjustmentSnap_'+label,leg(1.84,13.25),.25,.32)
        # Stitch the material seams using the exact clipped base interface.
    d=t.d;part=d['parts'][0];end=t.outer_count;fs=np.array(d['triangles'][:end]);slots=np.array(d['triangle_materials'][:end]);edges={}
    for f,slot in zip(fs,slots):
        for a,b in zip(f,np.roll(f,-1)):edges.setdefault(tuple(sorted((int(a),int(b)))),set()).add(int(slot))
    adj={}
    for (a,b),ss in edges.items():
        if ss=={0,2}:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    remaining=set(adj);ps=np.array(d['positions']);vn=normals(ps,fs)
    while remaining:
        start=next((i for i in remaining if len(adj[i])==1),min(remaining));path=[start];previous=None;cur=start;closed=False
        while True:
            available=[v for v in adj[cur] if v!=previous]
            if not available:break
            nxt=available[0]
            if nxt==start:closed=True;break
            if nxt in path:break
            path.append(nxt);previous,cur=cur,nxt
        remaining.difference_update(path)
        if len(path)>2:t.stitches('MobilityPanelSeam',[(ps[i]+vn[i]*.035,vn[i],d['weights'][i]) for i in path],closed)

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True);src,ps,fs,ws,uv=base();t=Tailor(src,ps,fs,ws,uv);t.shell();details(t)
    t.d['outer_shell_triangles']=t.outer_count
    write(R/'Authored'/ITEM/'Jason.json',t.d);write(R/'authored.json',dict(completed=True,concept='Design/LeatherPants_Concept02.png',approved=True,vertices=len(t.d['positions']),triangles=len(t.d['triangles']),parts=len(t.d['parts']),material_slots=SLOTS,native_bones=len(t.d['bones']),runtime_tested=False))
    print('RANGER_PANTS_AUTHORED',len(t.d['positions']),len(t.d['triangles']),flush=True)
if __name__=='__main__':main()
