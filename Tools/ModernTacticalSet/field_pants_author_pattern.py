"""MCDU-inspired sewn trouser panels, specified on full-size garment charts in cm."""
import numpy as np
import shapely
from scipy.interpolate import PchipInterpolator

from coyote_glove_author_patterns import tessellate


def ease(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def polygon(corners,rounding):
    poly=shapely.Polygon(corners)
    # Keep the military cut angular. Round the sewn corners by a few mm.
    if rounding:
        poly=poly.buffer(-rounding,join_style="mitre").buffer(rounding,quad_segs=4)
    return shapely.segmentize(poly,.58)


class Tailoring:
    def __init__(self,charts,side):
        self.charts=charts
        self.side=side
        self.pieces=[]

    def add(self,key,chart,q,heights,tri,slot):
        q=np.asarray(q)
        face,bary=self.charts[chart].locate(q)
        self.pieces.append(dict(name=self.side+"_"+key,chart=chart,face=face,w=bary,h=np.broadcast_to(heights,len(q)).copy(),
                                faces=np.asarray(tri),uv=q/8.,slot=slot))

    @staticmethod
    def height(fn,q):
        return np.broadcast_to(fn(q) if callable(fn) else fn,len(q))

    def piece(self,key,corners,slot,h,*,chart="leg",floor=.025,hem=.33,rounding=.32,step=.72,outline=None):
        poly=polygon(corners,rounding)
        q,faces,rings=tessellate(poly,step)
        dist=shapely.distance(shapely.points(q),poly.boundary)
        amp=self.height(h,q)
        level=floor+(amp-floor)*ease(dist/max(.01,hem))
        ring=rings[0];ids=np.arange(len(ring));nxt=np.roll(ids,-1);rim=ids+len(q)
        faces=np.vstack((faces,np.column_stack((ids,nxt,np.roll(rim,-1))),np.column_stack((ids,np.roll(rim,-1),rim))))
        self.add(key,chart,np.vstack((q,ring)),np.r_[level,np.full(len(ring),max(-.015,floor-.092))],faces,slot)
        if outline:
            line=poly.buffer(-outline[0]).exterior
            self.line(key+"_topstitch",list(line.coords),lambda p:self.height(h,p)+.018,chart=chart,width=outline[1],pitch=.49)
        return poly

    def line(self,key,points,height,*,chart="leg",width=.040,pitch=.46,material=4):
        path=shapely.LineString(points)
        n=max(1,round(path.length/pitch))
        step=path.length/n
        sample=((np.arange(n)[:,None]+.5+np.array([-.35,-.20,.20,.35]))*step).ravel()
        p=shapely.get_coordinates(shapely.line_interpolate_point(path,sample))
        a=shapely.get_coordinates(shapely.line_interpolate_point(path,np.maximum(0,sample-.018)))
        b=shapely.get_coordinates(shapely.line_interpolate_point(path,np.minimum(path.length,sample+.018)))
        norm=b-a;norm/=np.linalg.norm(norm,axis=1,keepdims=True).clip(1.e-9)
        norm=np.c_[-norm[:,1],norm[:,0]]
        radius=width*np.tile([.30,1.,1.,.30],n)
        q=np.stack((p+norm*radius[:,None],p,p-norm*radius[:,None]),axis=1)
        h=self.height(height,p)
        h=np.stack((h,h+radius*.72,h),axis=1)
        j=(np.arange(n)[:,None,None]*12+np.arange(3)[None,:,None]*3+np.arange(2)[None,None,:]).ravel()
        tri=np.r_[np.c_[j,j+1,j+4],np.c_[j,j+4,j+3]]
        self.add(key,chart,q.reshape(-1,2),h.ravel(),tri,material)

    def tape(self,key,points,width,slot,h,*,chart="leg",stitch=False):
        line=shapely.LineString(points)
        poly=line.buffer(width/2,cap_style="flat",join_style="round",quad_segs=3)
        self.piece(key,list(poly.exterior.coords)[:-1],slot,h,chart=chart,rounding=.025,
                   floor=max(.016,h-.11),hem=.08,step=.43)
        if stitch:
            self.line(key+"_stitch",points,h+.018,chart=chart)

    def cargo(self,name,u0,u1,rear=False):
        span=u1-u0
        bottom=58.3 if not rear else 59.0
        cap=79.2 if not rear else 78.5
        rise=4.8 if not rear else 3.3
        def lip(u):
            return cap-2.85+rise*u/span
        # A pleat needs a folded return in the cut topology. Add its crest,
        # near-vertical return and low lip as continuous strips. A free
        # Delaunay triangulation rounds away these narrow longitudinal edges.
        sections=np.unique(np.r_[np.linspace(0.,1.,21),.259,.304,.324,.337,.357,
                                  .698,.710,.722,.764,.815])
        rows=np.unique(np.r_[np.linspace(0.,1.,26),.025,.065,.94,.975])
        U,V=np.meshgrid(sections,rows);u=U.ravel();v=V.ravel()
        near=np.minimum(u,1.-u)*span
        lower=bottom+.55*(1.-u)+.65*np.maximum(1.-near/1.45,0.)
        upper=lip(span*u)+.89
        z=lower+(upper-lower)*v
        taper=ease(v/.14)*ease((1.-v)/.18)*ease(near/.54)
        sway=.085*np.sin(np.pi*(v-.04))*(1.-.25*v)
        shape=np.interp(u,[0.,.12,.259,.304,.324,.337,.357,.53,.68,.698,.710,.722,.764,.815,1.],
                       [0.,.07,.38,.69,.76,.10,.02,.04,.16,.30,.36,.09,.11,.045,0.])
        depth=.018+.16*ease(near/.48)*ease(v/.065)+taper*shape
        start=u0+.16+.42*(1.-v)+.28*np.sin(np.pi*v)
        end=u1-.12-.26*(1.-v)
        fraction=u+sway*np.sin(np.pi*u*2.0)
        outer=start+(end-start)*fraction
        q=np.c_[outer,z];count=len(sections);j=np.arange((len(rows)-1)*count)
        j=j[j%count<count-1]
        faces=np.r_[np.c_[j,j+1,j+count+1],np.c_[j,j+count+1,j+count]]
        self.add(name+"_bellows_bag","leg",q,depth,faces,0)
        for where in (.321,.709):
            uv=np.argmin(abs(sections-where))
            xyz=q.reshape(len(rows),count,2)[:,uv]
            for label,a,b in (("bottom",.025,.135),("top",.85,.97)):
                mask=(rows>=a)&(rows<=b)
                line=xyz[mask]
                level=depth.reshape(len(rows),count)[:,uv]
                self.line(name+"_pleat_tack_"+label+str(uv),line,lambda t:np.interp(t[:,1],xyz[:,1],level)+.017,width=.038,pitch=.35)
        self.line(name+"_bag_edge",[(u0+.83,lip(0)-.82),(u0+.93,bottom+1.4),
                    (u0+2.3,bottom+.62),(u1-1.98,bottom+.24),(u1-.79,bottom+1.07),
                    (u1-.45,lip(span)-.34)],.15,width=.041,pitch=.43)
        # Top facing is stitched almost flush. The turned lower edge curls
        # slightly over the gathered pocket mouth and casts a narrow shadow.
        def flap(q):
            x=q[:,0]-u0
            dist=q[:,1]-lip(x)
            return .16+.70*(1.-ease((dist+.12)/3.2))+.06*np.cos(x*.60)
        flap_c=[(u0-.26,lip(0)+.10),(u0-.29,lip(0)+3.27),(u0+.22,lip(0)+3.75),
                (u1-.24,lip(span)+3.73),(u1+.23,lip(span)+3.40),(u1+.14,lip(span)+.38),
                (u1-.48,lip(span)-.06),(u0+.57,lip(.57)-.09)]
        edge=[(u0-.13,lip(0)+.04),(u0+.65,lip(.65)-.11),(u1-.54,lip(span-.54)-.02),(u1+.09,lip(span)+.29)]
        self.tape(name+"_flap_turned_edge",edge,.24,2,.52)
        self.piece(name+"_turned_flap",flap_c,0,flap,floor=.49,hem=.14,rounding=.21,step=.47)
        for i,dz in enumerate((-.08,.20)):
            self.line(name+"_flap_stitch_"+str(i),[(u0+.32,lip(.32)+.37+dz),(u0+1.22,lip(1.22)+.29+dz),
                      (u1-.9,lip(span-.9)+.31+dz),(u1-.31,lip(span-.31)+.45+dz)],lambda q:flap(q)+.018,width=.035)
        if rear:
            self.piece(name+"_woven_pull",[(u0+1.55,cap-3.3),(u0+2.52,cap-3.18),
                       (u0+2.31,cap-5.06),(u0+1.60,cap-5.2)],3,.51,floor=.34,hem=.21,rounding=.11)

    def make(self):
        # In the official side photograph, each thigh has *two* pleated
        # pockets. A long zip separates the front and rear bags.
        self.cargo("Forward_cargo",-3.72,11.15)
        self.cargo("Rear_cargo",14.35,27.0,True)
        self.tape("Thigh_vent_welt",[(12.41,57.8),(12.73,65.3),(12.77,73.5),(12.73,82.1)],.94,1,.176)
        self.tape("Thigh_vent_zip",[(12.48,58.6),(12.76,65.3),(12.80,73.4),(12.76,81.4)],.265,3,.25)
        self.line("Zipper_coil",[(12.48,58.6),(12.76,65.3),(12.80,73.4),(12.76,81.35)],.274,width=.068,pitch=.18,material=5)
        self.piece("Zipper_slider",[(12.48,80.42),(13.03,80.4),(13.10,81.18),(12.78,81.44),(12.44,81.18)],
                   5,.45,floor=.28,hem=.15,rounding=.065,step=.20)
        self.piece("Folded_zipper_pull",[(12.32,78.15),(12.93,78.08),(13.06,80.69),(12.66,80.78)],
                   3,.58,floor=.39,hem=.18,rounding=.09,step=.26)

        # Hip hand-entry and back slip pocket using the pelvis chart. The tabs
        # are inset into the waist instead of extending above the existing belt.
        self.tape("Slanted_hip_entry",[(6.5,95.9),(7.9,93.7),(10.1,92.3),(15.6,91.5),(18.6,89.7)],
                  .88,2,.185,chart="hip",stitch=True)
        self.tape("Hip_entry_binding",[(6.4,95.8),(7.8,93.6),(10.0,92.2),(15.35,91.35),(18.4,89.6)],
                  .24,3,.219,chart="hip")
        self.tape("Rear_pocket_mouth",[(24.8,87.4),(28.1,87.1),(32.3,86.9),(36.4,86.75)],
                  .74,2,.158,chart="hip",stitch=True)
        mid=14.*np.pi
        yoke=[(21.9,94.92),(23.9,95.28),(41.6,95.65),(mid,95.65),(mid,89.68),
              (40.0,89.7),(34.6,90.0),(26.0,91.1),(22.3,91.11)]
        self.piece("Rear_stretch_yoke",yoke,1,.12,chart="hip",floor=.018,rounding=.24,hem=.29)
        self.line("Yoke_downturned_seam",[(22.86,91.45),(26,91.48),(34.7,90.40),(40.,90.09),(43.85,90.08)],
                  .136,chart="hip")

        # Sewn darts around a broad soft pad pocket, with no exposed molded
        # armour. A top-facing insertion welt and the under-knee tuck articulate
        # the leg at the same heights as the physical model.
        knee=[(-10.3,55.7),(-9.3,57.7),(-3.2,58.35),(3.85,58.9),(8.45,58.7),
              (10.12,56.7),(9.77,47.2),(8.15,40.0),(5.35,37.45),(-4.9,37.2),
              (-8.13,38.8),(-9.54,43.3)]
        def kneeh(q):
            u,z=q.T
            fullness=.38*np.exp(-((z-48.4)/7.5)**2-((u-.25)/8.)**4)
            medial=.18*np.exp(-((z-41.77+.11*(u+4.0))/.54)**2-((u+4.3)/2.4)**4)
            lateral=.23*np.exp(-((z-41.25-.31*(u-5.2))/.55)**2-((u-5.)/2.3)**4)
            return .065+fullness*.58+medial+lateral
        self.piece("Articulated_knee_pocket",knee,2,kneeh,floor=.055,hem=.45,rounding=.76,step=.55)
        self.line("Knee_insertion_doublewelt",[(-5.9,56.1),(-3.20,57.10),(.6,57.39),(3.92,57.48),(6.52,56.68)],lambda q:kneeh(q)+.025)
        for line,pts in (("medial",[(-6.5,42.0),(-4.0,41.48),(-1.05,41.92)]),
                         ("lateral",[(2.4,40.6),(5.2,41.25),(7.10,42.10)])):
            self.line("Prebend_dart_"+line,pts,lambda q:kneeh(q)+.021,width=.039)
        rear=[(17.4,52.35),(22.4,53.12),(27.3,53.28),(33.1,52.75),(35.0,51.54),
              (34.2,46.9),(31.25,43.90),(27.0,42.95),(21.4,43.35),(18.1,45.16)]
        self.piece("Posterior_knee_stretch",rear,1,lambda q:.11+.062*np.cos((q[:,1]-.24*q[:,0])*1.18)
                   *np.exp(-((q[:,0]-26.1)/5.2)**2-((q[:,1]-47.8)/3.55)**2),
                   floor=.018,hem=.32,rounding=.54,step=.52)
        self.tape("Rear_knee_adjustment",[(12.1,50.3),(16.2,50.8),(21.7,51.04),(26.4,50.91)],
                  1.62,3,.29,stitch=True)
        self.piece("Knee_tab_tip",[(19.7,50.0),(20.1,51.81),(25.85,51.91),(26.62,51.39),(26.41,50.17)],
                   2,.41,floor=.30,hem=.22,rounding=.30,step=.45)
        shin=[(8.6,17.29),(8.8,34.9),(10.35,36.74),(15.12,36.20),(17.73,32.00),(17.21,18.00),(15.2,16.92)]
        self.piece("Ankle_map_pocket",shin,0,lambda q:.20+.56*ease((q[:,1]-17.4)/4)*ease((36-q[:,1])/3)
                   *np.exp(-((q[:,0]-15.42)/2.4)**2),floor=.055,hem=.62,rounding=.40,step=.68)
        self.tape("Ankle_pocket_welt",[(9.33,34.21),(10.55,35.58),(14.65,35.11),(16.4,33.42)],.56,2,.28,stitch=True)
        self.tape("Ankle_adjustment_strap",[(7.65,16.35),(12.0,16.49),(16.5,16.70),(21.2,16.65)],1.74,3,.24,stitch=True)
        self.line("Lower_outseam",[(13.01,18.21),(12.99,25.0),(12.6,35.5),(12.03,42.7),(11.9,48.4)],
                  .052,width=.041,pitch=.48)
        return self.pieces
