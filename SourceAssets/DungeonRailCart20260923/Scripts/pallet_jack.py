"""Original, precisely modelled pallet jack; retains the freight bay footprint."""
import math
from mathutils import Vector
from rail_geometry import rounded


def build(h):
    box, tube, poly = h['box'], h['tube'], h['poly']
    detail = h['detail']
    kind = 'Props'
    def beam(a, b, width, depth, mat='PaintedSteel'):
        a, b = Vector(a), Vector(b)
        axis = (b-a).normalized()
        helper = Vector((0, 0, 1)) if abs(axis.z)<.9 else Vector((0, 1, 0))
        u = axis.cross(helper).normalized(); v = u.cross(axis).normalized()
        verts = [tuple(p+u*s*width/2+v*t*depth/2) for p in (a,b) for s,t in ((-1,-1),(1,-1),(1,1),(-1,1))]
        poly(kind, verts, [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)], mat)
    def wheel(x, y, z, r, width):
        axis = (1,0,0)
        # Separate rubber tyre, metal hub and bearing; the axle is no longer a giant wheel.
        detail.ring((x,y,z),axis,r,r*.59,width,'Rubber',40,kind)
        detail.ring((x,y,z),axis,r*.59,.013,width*.87,'BareSteel',32,kind)
        for s in (-1,1):
            p = (x+s*(width*.5+.002),y,z)
            detail.ring(p,axis,r*.32,.012,.012,'PaintedSteel',24,kind)
            detail.fastener(p,(s,0,0),.010,kind)
        for dx in (-width*.29,width*.29):
            detail.torus((x+dx,y,z),axis,r-.002,.002,kind,'Rubber',40)
    def profile_fork(x):
        # Chamfered toe, folded channel sides and open underside.
        outline=[(x-.072,10.725),(x+.072,10.725),(x+.095,10.80),
                 (x+.095,12.13),(x-.095,12.13),(x-.095,10.80)]
        n=len(outline)
        verts=[(xx,yy,(.127 if yy<10.80 else .182)+dz) for dz in (-.014,0) for xx,yy in outline]
        faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        poly(kind,verts,faces,'YellowPaint')
        for sign in (-1,1):
            xx=x+sign*.086
            box(kind,(xx,11.59,.131),(.018,1.02,.088),'YellowPaint')
            # Wheel fork cheek plates and the visible rocker pivot.
            box(kind,(xx,10.987,.083),(.014,.255,.085),'PaintedSteel')
            detail.fastener((xx+sign*.010,11.055,.092),(sign,0,0),.012,kind)
        for yy in (10.91,11.055):
            tube(kind,[(x-.10,yy,.062),(x+.10,yy,.062)],.012,'BareSteel',20)
            wheel(x,yy,.062,.062,.125)
        # Under-fork actuation rod and pivot connecting to the lift linkage.
        tube(kind,[(x,11.11,.087),(x,11.94,.087)],.012,'BareSteel',20)
        beam((x,11.94,.087),(x,12.09,.26),.038,.028)
        box(kind,(x,11.46,.184),(.135,.56,.003),'PaintedSteel')
        for yy in (11.15,11.78):
            detail.fastener((x,yy,.184),(0,0,1),.008,kind)
    for x in (1.10,1.68):
        profile_fork(x)
    # Folded rear crosshead and two reinforcing cheeks.
    box(kind,(1.39,12.055,.225),(.77,.20,.028),'YellowPaint')
    box(kind,(1.39,12.14,.325),(.69,.024,.22),'ServicePaint')
    box(kind,(1.39,12.01,.428),(.69,.28,.026),'ServicePaint')
    for x in (1.075,1.705):
        beam((x,11.93,.195),(x,12.13,.425),.024,.13,'ServicePaint')
        for z in (.27,.38):
            detail.fastener((x,12.158,z),(0,1,0),.011,kind)
    # Steering carrier, independent rear tyres, through axle and swivel thrust ring.
    for x in (1.26,1.52):
        wheel(x,12.235,.14,.14,.076)
    tube(kind,[(1.19,12.235,.14),(1.59,12.235,.14)],.019,'BareSteel',24)
    for x in (1.205,1.575):
        beam((x,12.235,.14),(x,12.195,.31),.025,.075)
    box(kind,(1.39,12.195,.314),(.395,.20,.024),'PaintedSteel')
    detail.ring((1.39,12.16,.35),(0,0,1),.098,.055,.048,'BareSteel',40,kind)
    # Cast pump barrel, polished ram, seal gland, release screw and filler cap.
    tube(kind,[(1.39,12.10,.33),(1.39,12.10,.515)],.071,'ServicePaint',40)
    detail.ring((1.39,12.10,.514),(0,0,1),.077,.032,.026,'BareSteel',40,kind)
    tube(kind,[(1.39,12.10,.516),(1.39,12.10,.59)],.030,'BareSteel',32)
    detail.ring((1.39,12.10,.53),(0,0,1),.036,.030,.008,'Rubber',32,kind)
    box(kind,(1.39,12.10,.604),(.17,.15,.028),'ServicePaint')
    detail.fastener((1.46,12.12,.458),(1,0,0),.012,kind)
    detail.fastener((1.39,12.035,.405),(0,-1,0),.010,kind)
    # Smaller pump plunger and exposed return spring beside the main cylinder.
    tube(kind,[(1.39,12.255,.325),(1.39,12.255,.443)],.027,'PaintedSteel',24)
    tube(kind,[(1.39,12.255,.436),(1.39,12.255,.51)],.012,'BareSteel',24)
    spring=[(1.39+.021*math.cos(i*math.tau/12),12.255+.021*math.sin(i*math.tau/12),.392+i*.0015) for i in range(61)]
    tube(kind,spring,.0035,'BareSteel',10)
    # Tiller clevis and pin, paired handle roots rather than a floating tube.
    for x in (1.355,1.425):
        beam((x,12.255,.44),(x,12.28,.58),.015,.055,'ServicePaint')
    tube(kind,[(1.335,12.275,.52),(1.445,12.275,.52)],.014,'BareSteel',24)
    for x,s in ((1.33,-1),(1.45,1)):
        detail.fastener((x,12.275,.52),(s,0,0),.012,kind)
    tube(kind,rounded([(1.39,12.275,.53),(1.39,12.35,.95),(1.39,12.36,1.03)],.045),.025,'PaintedSteel',32)
    grip=[(1.39,12.36,1.00),(1.15,12.36,1.14),(1.15,12.36,1.365),
          (1.63,12.36,1.365),(1.63,12.36,1.14),(1.39,12.36,1.00)]
    tube(kind,rounded(grip,.06),.024,'PaintedSteel',32)
    tube(kind,[(1.235,12.36,1.365),(1.545,12.36,1.365)],.029,'Rubber',32)
    for x in (1.23,1.55):
        detail.ring((x,12.36,1.365),(1,0,0),.030,.024,.016,'BareSteel',32,kind)
    beam((1.39,12.35,1.10),(1.48,12.32,1.285),.025,.017,'BareSteel')
    tube(kind,[(1.385,12.31,1.18),(1.385,12.30,.99),(1.385,12.26,.66),
               (1.39,12.22,.50)],.004,'Rubber',12)
    # Recessed capacity plate and restrained stamped lines use existing materials.
    box(kind,(1.39,12.157,.366),(.20,.003,.066),'BareSteel')
    for z in (.349,.366,.383):
        box(kind,(1.39,12.16,z),(.14,.002,.005),'PaintedSteel')
