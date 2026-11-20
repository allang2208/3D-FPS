"""Cut panels and thin sewn detail traced in anatomical glove surface charts."""
import numpy as np
import shapely
from scipy.interpolate import CubicSpline
from scipy.spatial import Delaunay
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

from coyote_glove_author_surface import SLOTS


def outline(ctrl,spacing=.16):
    a=np.array(ctrl,float);a=np.vstack((a,a[0]))
    t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(a,axis=0),axis=1))]
    return CubicSpline(t,a,bc_type="periodic")(np.linspace(0,t[-1],max(12,int(t[-1]/spacing)),endpoint=False))


def closed_line(poly):
    v=np.array(poly.exterior.coords)
    return shapely.LineString(v)


def rect(x0,y0,x1,y1,r):
    poly=shapely.box(x0+r,y0+r,x1-r,y1-r).buffer(r,quad_segs=4)
    return np.asarray(shapely.segmentize(poly,.17).exterior.coords)[:-1]


def tessellate(poly,step):
    boundaries=[np.asarray(v.coords)[:-1] for v in (poly.exterior,*poly.interiors)]
    a,b,c,d=poly.bounds
    interior=[]
    for i,y in enumerate(np.arange(b+step*.55,d,step*.865)):
        xs=np.arange(a+step*(.3+.5*(i%2)),c,step)
        interior.extend((x,y) for x in xs)
    if interior:
        interior=np.asarray(interior);keep=shapely.contains_xy(poly.buffer(-step*.43),*interior.T)
        interior=interior[keep]
    else:interior=np.empty((0,2))
    points=np.vstack([*boundaries,interior])
    tr=Delaunay(points).simplices
    pieces=shapely.polygons(points[tr])
    keep=shapely.covered_by(pieces,poly.buffer(.000005))
    f=tr[keep]
    # Preserve all constrained edges around the perforations and outline.
    # Insert any genuine sliver missed by the free Delaunay triangulation.
    lost=poly.difference(shapely.union_all(pieces[keep]))
    rest=[g for g in shapely.get_parts(lost) if g.area>1.e-7]
    if rest:
        lookup={tuple(np.round(v,6)):i for i,v in enumerate(points)}
        extra=[];new=list(points)
        for piece in rest:
            for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(piece)):
                row=[]
                for xy in list(tri.exterior.coords)[:3]:
                    key=tuple(np.round(xy,6))
                    if key not in lookup:lookup[key]=len(new);new.append(xy)
                    row.append(lookup[key])
                extra.append(row)
        points=np.array(new);f=np.vstack((f,np.array(extra,int).reshape(-1,3)))
    return points,f,boundaries


class Atelier:
    def __init__(self,hand):
        self.hand=hand;self.parts=[]

    def append(self,name,ch,q,height,f,material,uv=None):
        q=np.asarray(q);height=np.broadcast_to(height,len(q)).copy()
        ids,bary=ch.locate(q)
        self.parts.append(dict(name=self.hand.side+"_"+name,side=self.hand.side,
            anchor=ids,w=bary,height=height,faces=np.asarray(f,int),
            uv=(q/4 if uv is None else uv),mat=SLOTS.index("CG_"+material)))

    def panel(self,name,ch,edge,material,height,holes=(),floor=.008,step=.34,label=False):
        poly=shapely.Polygon(edge,holes)
        if not poly.is_valid:
            raise ValueError(f"Invalid tailoring outline {name}")
        points,tri,lines=tessellate(poly,step)
        distance=shapely.distance(shapely.points(points),poly.boundary)
        lift=floor+(height-floor)*np.sin(np.minimum(distance/.15,1.)*np.pi*.5)
        walls=[];base=[];index=0
        for loop in lines:
            n=len(loop);j=np.arange(n)+index;k=np.roll(j,-1)
            low=len(points)+index+np.arange(n)
            walls+=np.column_stack((j,k,np.roll(low,-1))).tolist()
            walls+=np.column_stack((j,np.roll(low,-1),low)).tolist()
            base.append(loop);index+=n
        allq=np.vstack((points,*base));h=np.r_[lift,np.full(index,max(-.003,floor-.026))]
        if label:
            a,b,c,d=poly.bounds
            u=(allq[:,0]-a)/(c-a);v=1.-(allq[:,1]-b)/(d-b)
            if self.hand.side=="r":u=1.-u
            uv=np.column_stack((u,v))
        else:uv=None
        self.append(name,ch,allq,h,np.vstack((tri,np.asarray(walls))),material,uv)
        return poly

    def seam(self,name,ch,curve,level=.065,width=.027,pitch=.235,material="Thread"):
        path=shapely.LineString(curve);length=path.length
        count=max(1,int(length/pitch))
        t=(np.arange(count)+.5)*length/count
        phase=np.array([-.31,-.18,0,.18,.31])*length/count
        station=(t[:,None]+phase[None,:]).ravel()
        pos=shapely.get_coordinates(shapely.line_interpolate_point(path,station))
        prev=shapely.get_coordinates(shapely.line_interpolate_point(path,np.maximum(0,station-.01)))
        after=shapely.get_coordinates(shapely.line_interpolate_point(path,np.minimum(length,station+.01)))
        tang=after-prev;tang/=np.maximum(1.e-8,np.linalg.norm(tang,axis=1,keepdims=True))
        norm=np.stack((-tang[:,1],tang[:,0]),axis=1)
        profile=np.tile([.30,.91,1.,.91,.30],count)*width
        q=np.stack((pos+norm*profile[:,None],pos,pos-norm*profile[:,None]),axis=1)
        bulge=profile*.63
        h=np.stack((np.full(len(pos),level),level+bulge,np.full(len(pos),level)),axis=1)
        floor=np.arange(count)[:,None,None]*15
        j=floor+np.arange(4)[None,:,None]*3+np.arange(2)[None,None,:]
        j=j.ravel()
        tr=np.vstack((np.column_stack((j,j+1,j+4)),np.column_stack((j,j+4,j+3))))
        self.append(name,ch,q.reshape(-1,2),h.ravel(),tr,material)

    def border(self,name,ch,p,level,offset=.09):
        contracted=p.buffer(-offset)
        for i,g in enumerate(shapely.get_parts(contracted)):
            if g.area>.02:self.seam(name+str(i),ch,g.exterior.coords,level)

    def letters(self,ch):
        # One-color textile transfer on the mesh back. The type is the
        # project's TS01 marking rather than the photographed manufacturer's.
        font=FontProperties(fname="C:/Windows/Fonts/arialbd.ttf")
        glyphs=TextPath((0,0),"TS01",size=1,prop=font).to_polygons()
        region=None
        for path in glyphs:
            shape=shapely.Polygon(path).buffer(0)
            region=shape if region is None else region.symmetric_difference(shape)
        xmin,ymin,xmax,ymax=region.bounds
        for i,g in enumerate(shapely.get_parts(region)):
            if g.area<.001:continue
            def mapped(loop):
                q=np.array(loop.coords)[:-1].copy()
                q[:,0]=(q[:,0]-(xmax+xmin)*.5)*5.35/(xmax-xmin)
                q[:,1]=(q[:,1]-(ymax+ymin)*.5)*1.18/(ymax-ymin)
                if self.hand.side=="r":q[:,0]*=-1
                q[:,1]+=.16*q[:,0]+6.1;q[:,0]-=.5
                return q
            self.panel("Dorsal_knit_transfer_"+str(i),ch,mapped(g.exterior),"Webbing",.027,
                       holes=[mapped(l) for l in g.interiors],floor=.021,step=.30)

    def cut(self):
        back=self.hand.panel[1];palm=self.hand.panel[-1]
        # The photographed closure lies against the free edge, not above the
        # wrist joint. Locate that edge on the actual shell of this template.
        local=self.hand.all.reshape(-1,3)
        center=local[np.abs(local[:,0])<1.9,1]
        cuff_y=float(np.percentile(center,1))+.25
        class CuffChart:
            def __init__(self,surface):self.surface=surface
            def locate(self,q):
                q=np.asarray(q).copy()
                q[:,0]*=1.09
                q[:,1]=q[:,1]*1.34+cuff_y
                return self.surface.locate(q)
        wrist=CuffChart(back)
        wrist_inside=CuffChart(palm)
        # Narrow sewn seam at the radius and ulna leaves the central textile
        # and all four MCP joints unpadded, as in the dorsal photograph.
        dorsal_lines=[[(2.55,1.65),(2.8,2.28),(2.93,2.88),(3.19,3.50),(3.32,4.04)],
                      [(-2.80,1.78),(-3.22,2.30),(-3.54,3.05),(-3.74,4.05),(-3.92,5.3),(-4.06,6.45)]]
        for i,line in enumerate(dorsal_lines):self.seam("Hand_side_felling_"+str(i),back,line,.035,.024)
        # Thin velour reinforcement with actual holes and an independent
        # dark textile backing visible through them. The pad never thickens
        # the grip-bearing finger pads.
        heel=outline([(-3.07,1.05),(-3.40,2.00),(-3.77,3.85),(-3.76,5.12),
            (-3.16,5.56),(-1.73,5.37),(-.48,4.89),(.69,4.37),(1.73,3.65),
            (2.43,2.35),(2.20,1.07),(.88,.77),(-1.28,.85)])
        holes=[]
        for y,xs in ((2.1,[-2.58,-1.60,-.57]),(2.68,[-2.98,-2.08,-1.12,-.15]),
                     (3.26,[-2.67,-1.68,-.70]),(3.8,[-2.2,-1.23])):
            for x in xs:
                angles=np.arange(10)*2*np.pi/10
                holes.append(np.column_stack((x+.082*np.cos(angles),y+.082*np.sin(angles))))
        self.panel("Heel_perforation_backer",palm,outline([(-3.25,1.8),(-3.17,3.5),(-2.6,4.15),(-.8,4.12),(.22,3.8),(.28,2.2),(-.36,1.69)]),"Stretch",.038,floor=.019)
        heelpoly=self.panel("Perforated_suede_palm_heel",palm,heel,"Suede",.134,holes,.058)
        self.border("Palm_heel_topstitch",palm,shapely.Polygon(heel),.127,.115)
        self.seam("Palm_flex_fold",palm,[(-3.84,6.82),(-3.20,7.20),(-2.25,7.22),(-1.1,7.04),(.15,6.86),(1.63,6.62)],.033,.026)
        saddle=outline([(1.87,1.35),(2.52,1.42),(3.02,2.42),(3.50,3.48),(3.65,4.54),
            (3.42,5.30),(2.83,5.02),(2.34,4.49),(1.68,3.98),(1.29,3.29),(1.37,2.48)])
        self.panel("Welded_thumb_saddle",palm,saddle,"Suede",.073,floor=.021)
        self.seam("Saddle_edge_stitch",palm,[(1.60,2.51),(1.59,3.27),(1.81,3.78),(2.41,4.27),(3.16,4.84)],.070,.025)
        # Captured side profile shows a single low hooked wrist tab with
        # angled ribbing, centered ID window and stitched stretch cuff.
        cuff=outline([(-2.70,-.04),(-2.64,.55),(-2.1,1.19),(-.72,1.67),(1.03,1.78),
                      (2.69,1.62),(2.89,1.25),(2.75,.43),(1.85,.18),(.08,.03),(-1.85,-.15)])
        p=self.panel("Cuff_hook_fabric_tongue",wrist,cuff,"Webbing",.13,floor=.065)
        self.border("Cuff_hemming",wrist,p,.121,.095)
        rubber=outline([(-2.50,.12),(-2.37,.68),(-1.63,1.09),(-.43,1.41),(1.26,1.51),
                       (2.51,1.37),(2.55,.69),(2.12,.45),(.60,.29),(-1.43,.09)])
        self.panel("Low_profile_TPR_wrist_tab",wrist,rubber,"Rubber",.245,floor=.13)
        label=rect(-.94,.44,1.12,1.35,.14)
        self.panel("Wrist_TS01_label",wrist,label,"Label",.287,floor=.258,label=True)
        for i,x in enumerate([-2.14,-1.84,-1.53,-1.21,1.29,1.59,1.90,2.16]):
            cy=.71+.095*x
            lower=cy-.16;upper=cy+.14+.08*(1-abs(x)/2.6)
            y1=x+.12 if x<0 else x-.11
            rib=outline([(x-.06,lower),(x+.05,lower-.01),(y1+.06,upper),(y1-.03,upper+.04)],.08)
            self.panel("Wrist_tab_rib_"+str(i),wrist,rib,"Rubber",.314,floor=.242,step=.18)
        self.seam("Wrist_flex_upper",wrist,[(-2.68,1.79),(-1.83,1.97),(-.97,2.11),(.05,2.22),(1.23,2.24),(2.50,2.02)],.042)
        wrap=outline([(-2.72,.36),(-2.22,.18),(.92,.23),(2.30,.40),(2.60,.76),
                      (2.26,1.17),(.82,1.26),(-1.80,1.15),(-2.72,.91)])
        wrap_edge=self.panel("Palmar_cuff_wrap",wrist_inside,wrap,"Webbing",.113,floor=.044)
        self.border("Palmar_wrap_topstitch",wrist_inside,wrap_edge,.115,.098)
        tip=outline([(-2.58,.40),(-2.59,.86),(-2.24,1.01),(-.34,1.03),
                     (-.04,.84),(-.08,.47),(-.49,.34),(-2.27,.30)])
        self.panel("Palmar_closure_grip",wrist_inside,tip,"Rubber",.175,floor=.112)
        self.letters(back)
        for digit,(ch,L,r) in self.hand.digits.items():
            width=min(r*1.02,.98)
            # Knit ends follow a tapered horseshoe on the dorsal phalanx,
            # leaving the soft synthetic leather wrapped round the fingertip.
            cap=outline([(-width*.9,L*.59),(-width*.86,L*.67),(-width*.45,L*.725),
                         (width*.36,L*.733),(width*.82,L*.70),(width*.98,L*.65),
                         (width*.98,L*.79),(width*.66,L*.858),(-width*.45,L*.86),(-width*.90,L*.81)],.13)
            self.panel(digit+"_fingertip_weld",ch,cap,"Suede",.052,floor=.022,step=.24)
            self.seam(digit+"_dorsal_tip_lockstitch",ch,[(-width*.76,L*.66),(-width*.45,L*.708),
                (0,L*.725),(width*.47,L*.718),(width*.8,L*.69)],.058,.021,pitch=.205)
            for sg in (-1,1):
                self.seam(digit+("_radial" if sg>0 else "_ulnar")+"_fourchette",ch,[
                    (sg*1.15*r,L*.18),(sg*1.17*r,L*.32),(sg*1.19*r,L*.48),
                    (sg*1.16*r,L*.61),(sg*1.02*r,L*.71)],.045,.021,pitch=.222)
            if digit=="thumb":
                tab=outline([(-.89*r,.24*L),(-1.18*r,.44*L),(-.90*r,.60*L),
                    (-.39*r,.61*L),(.04*r,.49*L),(.34*r,.31*L),(.09*r,.19*L)],.14)
                self.panel("Thumb_lock_wrap",ch,tab,"Suede",.080,floor=.030,step=.28)
        return self.parts
