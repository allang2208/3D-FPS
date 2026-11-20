"""Sew the patrol shirt details on the actual triangles of each native sleeve."""
import argparse
import gzip
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import shapely
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon

from coyote_glove_author_patterns import tessellate
from patrol_shirt_sleeves import DEST, ROOT, SET, SLOTS, plan, read


def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1.e-12)


def smooth(x):
    x=np.clip(x,0.,1.)
    return x*x*(3.-2.*x)


def normals(p,f):
    n=np.zeros_like(p)
    face=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    for k in range(3):
        np.add.at(n,f[:,k],face)
    return unit(n)


class Sleeve:
    def __init__(self,vertices,faces,bones,side):
        self.p=vertices
        shoulder,elbow,wrist=[np.asarray(bones[n+"_"+side]["position"]) for n in ("upperarm","lowerarm","hand")]
        u,v=unit(elbow-shoulder),unit(wrist-elbow)
        self.upper,self.lower=np.linalg.norm(elbow-shoulder),np.linalg.norm(wrist-elbow)
        # The native elbow plane supplies the rear dart direction even for a
        # pre-bent bind pose. Neutral Super90 has its own native bone axes.
        bend=v-u*np.dot(v,u)
        if np.linalg.norm(bend)>.16:
            posterior=-unit(bend)
        else:
            posterior=unit(np.array([0.,1.,0.])-u*u[1])
        lateral=unit(np.cross(posterior,u))
        opposite=np.array(bones["upperarm_"+("r" if side=="l" else "l")]["position"])
        if np.dot(lateral,shoulder-opposite)<0:
            lateral=-lateral
        lower_lateral=unit(lateral-v*np.dot(lateral,v))
        lower_back=unit(np.cross(v,lower_lateral))
        upper_back=unit(np.cross(u,lateral))
        if np.dot(upper_back,posterior)<0:
            upper_back=-upper_back
            lower_back=-lower_back
        bisector=unit(u+v)
        rel=vertices-elbow
        upper=rel@bisector<0
        axis=np.where(upper[:,None],u,v)
        near=(rel@bisector)/max(.2,u@bisector)
        far=(rel*axis).sum(1)
        fade=smooth(abs(near)/9.)
        s=near*(1-fade)+far*fade
        around=(rel*np.where(upper[:,None],lateral,lower_lateral)).sum(1)
        behind=(rel*np.where(upper[:,None],upper_back,lower_back)).sum(1)
        # Coordinates in cm. X wraps around the arm and Y runs towards the wrist.
        self.radius=5.
        theta=np.arctan2(behind,around)
        self.q=np.column_stack((theta*self.radius,s))
        self.period=2*np.pi*self.radius
        uv=self.q[faces].copy()
        uv[:,:,0]=uv[:,:1,0]+((uv[:,:,0]-uv[:,:1,0]+self.period/2)%self.period)-self.period/2
        self.anchors=np.tile(faces,(3,1))
        self.chart=np.concatenate([uv+[shift,0.] for shift in (-self.period,0.,self.period)])
        self.kd=cKDTree(self.chart.mean(1))
        self.n=normals(vertices,faces)
        edges=np.sort(np.vstack((faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]])),axis=1)
        edges,counts=np.unique(edges,return_counts=True,axis=0)
        border=np.unique(edges[counts==1])
        cuff=border[s[border]>.5*self.lower]
        if len(cuff)<8:
            raise ValueError("Missing native wrist opening on "+side)
        self.rim_q=self.q[cuff]
        self.rim_q=self.rim_q[np.argsort(self.rim_q[:,0])]

    def rim(self,x):
        return np.interp(x,self.rim_q[:,0],self.rim_q[:,1],period=self.period)

    def anchor(self,q):
        _,cand=self.kd.query(q,k=28)
        tri=self.chart[cand]
        e1,e2=tri[:,:,1]-tri[:,:,0],tri[:,:,2]-tri[:,:,0]
        d=q[:,None,:]-tri[:,:,0]
        def cross(a,b):
            return a[...,0]*b[...,1]-a[...,1]*b[...,0]
        den=cross(e1,e2)
        safe=np.where(abs(den)>1e-8,den,1.)
        v,w=cross(d,e2)/safe,cross(e1,d)/safe
        bary=np.stack((1-v-w,v,w),axis=-1)
        score=np.min(bary,axis=2)
        score[abs(den)<1e-8]=-1e6
        choice=np.argmax(score,axis=1)
        rows=np.arange(len(q))
        ids=self.anchors[cand[rows,choice]]
        weights=np.maximum(0.,bary[rows,choice])
        return ids,weights/weights.sum(1,keepdims=True)

    def folds(self):
        # Small compression pleats gather on the front of the elbow and
        # release into the forearm. Native cuff and shoulder boundaries are pinned.
        x,s=self.q.T
        theta=x/self.radius
        anterior=np.maximum(-np.sin(theta),0.)**1.4
        oblique=.95*np.cos(theta)+.32*np.sin(theta*2)
        amount=.14*np.exp(-((s-.7)/5.5)**2)
        for row,height in ((-3.,.26),(.05,.34),(3.15,.26),(6.1,.16)):
            t=s-row-oblique
            amount+=anterior*(height*np.exp(-(t/.65)**2)-.10*np.exp(-((t+.8)/.47)**2))
        end=smooth((self.rim(x)-s-5.5)/3.)*smooth((s+self.upper-4.)/3.)
        return self.n*(amount*end)[:,None]


class Pattern:
    def __init__(self,sleeve,side):
        self.s,self.side=sleeve,side
        self.cuts=[]

    def piece(self,label,q,h,faces,mat,uv=None):
        q=np.asarray(q)
        anchors,bary=self.s.anchor(q)
        normal=unit(np.sum(self.s.n[anchors]*bary[:,:,None],axis=1))
        p=np.sum(self.s.p[anchors]*bary[:,:,None],axis=1)+normal*np.asarray(h)[...,None]
        f=np.asarray(faces).copy()
        xyz=p[f]
        fn=np.cross(xyz[:,2]-xyz[:,0],xyz[:,1]-xyz[:,0])
        keep=np.linalg.norm(fn,axis=1)>1.e-8
        f,fn=f[keep],fn[keep]
        reverse=(fn*normal[f].mean(1)).sum(1)<0
        f[reverse]=f[reverse,::-1]
        return dict(name=self.side+"_"+label,p=p,f=f,n=normals(p,f),uv=q/8. if uv is None else uv,
                    ids=anchors,mix=bary,slot=SLOTS.index("PS_"+mat))

    def panel(self,label,region,mat,height,low=.028,step=.51,hem=False):
        q,f,loops=tessellate(region,step)
        dist=shapely.distance(shapely.points(q),region.boundary)
        lift=low+(height-low)*smooth(dist/.18)
        if hem:
            # Bottom fold lifts slightly over the following layer.
            lift+=.075*np.exp(-((q[:,1]-region.bounds[3]+.56)/.42)**2)
        self.cuts.append(self.piece(label,q,lift,f,mat))
        for i,r in enumerate(loops):
            n=len(r);j=np.arange(n);k=(j+1)%n
            faces=np.vstack((np.stack((j,k,k+n),1),np.stack((j,k+n,j+n),1)))
            wall=self.piece(label+"_edge"+str(i),np.vstack((r,r)),np.r_[np.full(n,low),np.full(n,.008)],faces,mat,
                np.vstack((np.c_[np.r_[0,np.cumsum(np.linalg.norm(np.diff(r,axis=0),axis=1))],np.ones(n)*low],
                           np.c_[np.r_[0,np.cumsum(np.linalg.norm(np.diff(r,axis=0),axis=1))],np.zeros(n)]))/8.)
            self.cuts.append(wall)

    def stitch(self,label,path,height,width=.034,spacing=.32,material="Thread"):
        line=LineString(path);count=int(line.length/spacing)
        if not count: return
        offsets=np.array([-.32,0.,.32])*line.length/count
        t=((np.arange(count)[:,None]+.5)*line.length/count+offsets).reshape(-1)
        def sample(d):
            return shapely.get_coordinates(shapely.line_interpolate_point(line,np.clip(t+d,0,line.length)))
        q=sample(0.);tangent=unit(sample(.016)-sample(-.016));w=width*np.tile([.4,1.,.4],count)
        a=np.stack((-tangent[:,1],tangent[:,0]),1)*w[:,None]
        points=np.stack((q-a,q,q+a),1).reshape(-1,2)
        h=np.tile(np.c_[np.zeros(3),[0.,.039,0.],np.zeros(3)].ravel(),count)+height
        j=(np.arange(count)[:,None]*9+np.array([0,1,3,4])).ravel()
        f=np.vstack((np.stack((j,j+1,j+4),1),np.stack((j,j+4,j+3),1)))
        self.cuts.append(self.piece(label,points,h,f,material))

    def edge(self,label,region,height,offset=.18):
        inner=region.buffer(-offset)
        for j,p in enumerate(shapely.get_parts(inner)):
            if isinstance(p,Polygon):self.stitch(label+str(j),p.exterior.coords,height)

    def sew(self):
        s=self.s
        def patch(points,r=.20):
            return shapely.segmentize(Polygon(points).buffer(-r).buffer(r,quad_segs=3),.30)
        # Broad three-lobed reinforced pocket with curved dart cuts on the
        # olecranon. Keep fabric under the edges; there is no projecting hard pad.
        x=6.7
        elbow=patch([(x-3.7,-5.1),(x-2.0,-6.7),(x+1.65,-6.3),(x+3.7,-4.1),
                     (x+3.75,-1.),(x+3.17,.45),(x+3.46,2.6),(x+2.9,6.0),
                     (x+1.1,8.0),(x-1.1,8.25),(x-2.9,6.7),(x-3.35,3.8),(x-3.0,1.4),(x-3.65,-.25)])
        self.panel("articulated_elbow",elbow,"Reinforcement",.145,.055)
        self.edge("elbow_topstitch",elbow,.166)
        for i,a in enumerate((-1,1)):
            self.stitch("elbow_dart_"+str(i),[(x+a*3.38,-1.25),(x+a*2.75,-.29),(x+a*1.78,.03)],.162)
        # Sloped sleeve pocket with a zipper on its front edge and individual
        # loop panels, as on the coyote MCDU reference.
        c=-s.upper*.53
        pocket=patch([(-3.96,c-4.25),(2.6,c-4.60),(3.78,c-3.12),(3.76,c+4.75),
                      (2.66,c+5.58),(-2.98,c+5.37),(-3.75,c+4.48)],.32)
        self.panel("upper_arm_pocket",pocket,"Ripstop",.32,.09,hem=True)
        self.edge("pocket_stitch",pocket,.334,.27)
        for i,(y0,y1) in enumerate(((-3.65,-1.23),(-.83,3.99))):
            loop=patch([(-2.30,c+y0),(2.18,c+y0-.21),(2.23,c+y1),( -2.28,c+y1+.22)],.13)
            self.panel("loop_field_"+str(i),loop,"Loop",.412,.351)
            self.edge("loop_tack_"+str(i),loop,.418,.14)
        zipper=LineString([(-3.00,c-3.95),(-3.02,c-1.0),(-2.92,c+2.0),(-2.71,c+4.34)])
        tape=shapely.segmentize(zipper.buffer(.22,quad_segs=3),.28)
        self.panel("pocket_zip_tape",tape,"Binding",.403,.355,.4)
        self.stitch("zip_coil",zipper.coords,.424,.070,.20,"Hardware")
        handle=patch([(-3.22,c-3.97),(-2.70,c-4.07),(-2.53,c-3.45),(-2.88,c-2.60),(-3.16,c-2.64)],.07)
        self.panel("rounded_zip_slider",handle,"Hardware",.56,.43,.16)
        # A close-fitting tab and loop field follow the irregular native
        # wrist margin independently at every angular sample.
        def cuff_polygon(profile):
            raw=shapely.segmentize(Polygon(profile),.24)
            q=np.asarray(raw.exterior.coords).copy()
            q[:,1]=s.rim(q[:,0])-q[:,1]
            return Polygon(q)
        landing=cuff_polygon([(-5.0,1.05),(2.8,1.1),(3.25,1.55),(3.05,3.50),(-4.74,3.69),(-5.1,3.31)])
        self.panel("cuff_landing",landing,"Loop",.147,.082,.36)
        self.edge("cuff_landing_stitch",landing,.158,.15)
        tab=cuff_polygon([(-1.65,1.22),(-.83,.98),(4.97,1.10),(6.14,.72),(6.90,.82),
                                 (6.88,3.81),(5.98,3.84),(4.86,3.30),(-.89,3.31),(-1.76,2.77)])
        self.panel("adjustable_cuff_tab",tab,"Ripstop",.253,.16,.37)
        self.edge("tab_stitch",tab,.272,.16)
        for j,offset in enumerate((.39,.78)):
            xline=np.linspace(-15.6,15.6,102)
            self.stitch("turned_cuff_stitch_"+str(j),np.c_[xline,s.rim(xline)-offset],.038)
        # The seam runs along the sleeve and branches away from the elbow cup.
        path=[(-6.6,-s.upper*.72),(-6.48,-s.upper*.45),(-6.2,-4.),(-5.72,2.3),
              (-5.89,7.2),(-6.22,s.rim(-6.22)-4.45)]
        self.stitch("inseam",path,.036,.032,.36)


def build(rig):
    row=plan()["rigs"][rig]
    data=read(SET/row["source"])
    old=read(SET/"CombatShirtR3/Authored"/("shirt_fp_"+rig+".json"))
    parts=old["parts"]
    face_count=max(v["first_triangle"]+v["triangles"] for v in parts)
    vertices=max(v["first_vertex"]+v["vertices"] for v in parts)
    p=np.asarray(data["positions"][:vertices])
    f=np.asarray(data["triangles"][:face_count])
    uv=np.asarray(data["uv"][:face_count])
    weights=data["weights"][:vertices]
    material=np.asarray(data["triangle_materials"][:face_count]).tolist()
    bones={b["name"]:b for b in data["bones"]}
    cuts=[];ranges={}
    for part in parts:
        side=part["name"][-1];start=part["first_vertex"];count=part["vertices"]//2
        outside=((f>=start)&(f<start+count)).all(1)
        tri=f[outside]-start
        native=Sleeve(p[start:start+count],tri,bones,side)
        displacement=native.folds()
        p[start:start+count]+=displacement
        p[start+count:start+2*count]+=displacement
        native.n=normals(native.p,tri)
        pattern=Pattern(native,side);pattern.sew()
        for cut in pattern.cuts:
            cut["ids"]+=start
            cuts.append(cut)
        ranges[side+"_native_sleeve"]=[part["first_triangle"],part["first_triangle"]+part["triangles"]]
    base_normals=normals(p,f)
    all_p=[p];all_f=[f];all_uv=[uv];all_n=[base_normals[f]]
    cursor=vertices;fi=face_count
    for cut in cuts:
        cp,cf=cut["p"],cut["f"]
        for ids,mix in zip(cut["ids"],cut["mix"]):
            combined={}
            for idx,factor in zip(ids,mix):
                for bone,value in weights[idx]:
                    combined[bone]=combined.get(bone,0.)+value*factor
            ordered=sorted(((b,v) for b,v in combined.items() if v>.00005),key=lambda v:-v[1])[:8]
            total=sum(v for _,v in ordered)
            weights.append([(b,round(v/total,7)) for b,v in ordered])
        all_p.append(cp);all_f.append(cursor+cf);all_uv.append(cut["uv"][cf]);all_n.append(cut["n"][cf])
        material.extend([cut["slot"]]*len(cf));ranges[cut["name"]]=[fi,fi+len(cf)]
        cursor+=len(cp);fi+=len(cf)
    out=dict(source=data["source"],skeleton=data["skeleton"],bones=data["bones"],rig=rig,
             positions=np.concatenate(all_p).round(6).tolist(),triangles=np.concatenate(all_f).tolist(),
             weights=weights,normals=np.concatenate(all_n).round(6).tolist(),uv=np.concatenate(all_uv).round(7).tolist(),
             material_slots=SLOTS,materials=[DEST+"/Materials/M_"+s for s in SLOTS],triangle_materials=material,parts=ranges,
             native_source_sha256=row["source_sha256"],cuff_underlap="Native inner and outer wrist geometry and binding preserved through 5.5 cm of the cut.")
    target=ROOT/row["authored"];target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix(".tmp")
    with gzip.open(temp,"wt",encoding="utf8",compresslevel=2) as stream:
        json.dump(out,stream,separators=(",",":"),allow_nan=False)
    temp.replace(target)
    return rig,fi


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("rig",nargs="*")
    args=parser.parse_args()
    rigs=args.rig or list(plan()["rigs"])
    with ProcessPoolExecutor(min(4,len(rigs))) as pool:
        for rig,count in pool.map(build,rigs):
            print("Sewn",rig,count,flush=True)
