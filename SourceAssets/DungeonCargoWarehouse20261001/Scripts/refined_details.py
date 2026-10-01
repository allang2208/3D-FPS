"""Reusable warehouse refinements: mechanically connected hoist and painted routing."""
def build_hoist():
    # Runway beams bear on the real columns at y=8/13; bridge wheels sit on these rails.
    for x in (-14.40,14.40):
        for z in (7.06,7.44):box('Hoist',(x,10.5,z),(.40,5.0,.055),'PaintedSteel')
        box('Hoist',(x,10.5,7.25),(.045,5,.34),'PaintedSteel')
        for y in (8,13):box('Hoist',(x,y,7.50),(.52,.18,.25),'Yellow')
        for y in (10.65,11.35):
            lathe('Hoist',(x-.14,y,7.60),(1,0,0),[(0,.16),(.05,.18),(.23,.18),(.28,.16)],'BareSteel',40)
        box('Hoist',(x,11,7.83),(.48,1.30,.18),'Yellow')
    for z in (7.54,8.05):box('Hoist',(0,11,z),(28.8,.54,.065),'PaintedSteel')
    box('Hoist',(0,11,7.80),(28.8,.065,.46),'Yellow')
    # Travelling trolley around the underside flange, bolted gearbox and motor.
    box('Hoist',(2,11,7.27),(1.22,.94,.35),'Yellow')
    for x in (1.56,2.44):
        for y in (10.74,11.26):
            lathe('Hoist',(x,y-.055,7.60),(0,1,0),[(0,.12),(.11,.12)],'BareSteel',36)
    lathe('Hoist',(2,10.44,7.14),(0,1,0),[(0,.25),(.12,.27),(.84,.27),(.95,.25)],'PaintedSteel',48)
    for x in (1.57,2.43):
        for z in (7.13,7.39):detail.fastener((x,10.515,z),(0,-1,0),.022,'HoistHook')
    for yy in (10.78,11.22):
        detail.tube('HoistChain',[(2,yy,7.08),(2,yy,3.08)],.012,'BareSteel',16)
    arc=[(2,11+.22*math.cos(t),3.08+.22*math.sin(t)) for t in [math.pi+i*math.pi/40 for i in range(41)]]
    detail.tube('HoistChain',arc,.012,'BareSteel',16)
    # Closed side cheeks enclose the load sheave, with shaft, spacers and retaining nuts.
    for x in (1.76,2.24):
        box('HoistHook',(x,11,3.08),(.045,.60,.60),'Yellow')
        lathe('HoistHook',(x-.045,11,3.08),(1,0,0),[(0,.095),(.09,.095)],'BareSteel',48)
        detail.fastener((x+(-.055 if x<2 else .055),11,3.08),(-1 if x<2 else 1,0,0),.045,'HoistHook')
        for dy in (-.21,.21):
            for dz in (-.20,.20):detail.fastener((x+(-.03 if x<2 else .03),11+dy,3.08+dz),(-1 if x<2 else 1,0,0),.018,'HoistHook')
    lathe('HoistHook',(1.8,11,3.08),(1,0,0),[(0,.235),(.035,.235),(.08,.206),(.32,.206),(.365,.235),(.40,.235)],'BareSteel',64)
    box('HoistHook',(2,11,2.80),(.50,.29,.08),'PaintedSteel')
    lathe('HoistHook',(2,11,2.60),(0,0,1),[(0,.062),(.035,.085),(.07,.085),(.08,.063),(.20,.063)],'BareSteel',48)
    detail.ring((2,11,2.72),(0,0,1),.108,.064,.07,'BareSteel',48,'HoistHook')
    # Smooth variable cross-section, forged rather than a bent constant-diameter tube.
    curves=[([(2,2.63),(2,2.48),(1.90,2.4),(1.92,2.25)],.046,.073),
        ([(1.92,2.25),(1.94,2.04),(2.18,1.98),(2.34,2.14)],.073,.059),
        ([(2.34,2.14),(2.45,2.24),(2.41,2.38),(2.34,2.44)],.059,.014)]
    path=[]
    for j,(control,r0,r1) in enumerate(curves):
        ps=[Vector((x,11,z)) for x,z in control]
        for i in range(25):
            if j and i==0:continue
            t=i/24;p=(1-t)**3*ps[0]+3*(1-t)**2*t*ps[1]+3*(1-t)*t*t*ps[2]+t**3*ps[3]
            path.append((p,r0+(r1-r0)*t))
    vs=[];fs=[];uv=[]
    for i,(p,r) in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)][0]-path[max(0,i-1)][0]).normalized()
        across=Vector((0,1,0));radial=tangent.cross(across).normalized()
        for k in range(24):
            t=k*math.tau/24;vs.append(p+radial*(r*math.cos(t))+across*(r*.72*math.sin(t)))
    for i in range(len(path)-1):
        for k in range(24):fs.append((i*24+k,i*24+(k+1)%24,(i+1)*24+(k+1)%24,(i+1)*24+k))
    fs.extend([tuple(reversed(range(24))),tuple((len(path)-1)*24+k for k in range(24))])
    poly('HoistHook',vs,fs,'BareSteel',smooth=[True]*(len(fs)-2)+[False,False])
    # Spring-loaded throat latch joins the upper heel and inside of the hook tip.
    beam('HoistHook',(2.025,11,2.50),(2.333,11,2.415),.075,.010,'BareSteel')
    lathe('HoistHook',(2.025,10.95,2.50),(0,1,0),[(0,.027),(.10,.027)],'BareSteel',32)
    for yy in (10.968,10.984,11,11.016,11.032):detail.torus((2.025,yy,2.50),(0,1,0),.026,.004,'HoistHook','BareSteel',20)

def build_floor_markings():
    MAPPING['FloorPaint']=CFG['ue_base']+'/RefineV2/Materials/M_CargoWarehouse_FloorPaint'
    MATS['FloorPaint']=bpy.data.materials.new('RS_FloorPaint')
    def triangles(vertices):
        indices={tuple(v):i for i,v in enumerate(vertices)}
        faces=[]
        for f in tessellate_polygon([vertices]):
            a,b,c=[i if isinstance(i,int) else indices[tuple(i)] for i in f]
            if (vertices[b]-vertices[a]).cross(vertices[c]-vertices[a]).z<0:b,c=c,b
            faces.append((a,b,c))
        return faces
    # One joined outline per edge, open across the door thresholds.
    # Paint sits 2.5 mm above the paving with no stacked box surfaces.
    def stroke(points,width=.11):
        ps=[Vector((x,y,.0045)) for x,y in points];left=[];right=[]
        for i,p in enumerate(ps):
            d0=(ps[i]-ps[i-1]).normalized() if i else (ps[1]-p).normalized()
            d1=(ps[i+1]-p).normalized() if i<len(ps)-1 else d0
            n0=Vector((-d0.y,d0.x,0));n1=Vector((-d1.y,d1.x,0));m=(n0+n1).normalized()
            off=m*(width*.5/max(.35,m.dot(n0)))
            left.append(p+off);right.append(p-off)
        verts=left+list(reversed(right))
        poly('FloorMarkings',verts,triangles(verts),'FloorPaint')
    stroke([(-14.6,-11.05),(2.3,-11.05),(2.3,2.95),(14.6,2.95)])
    # Step around the eastern stair footprint (y starts at 6.28 m).
    stroke([(14.6,7.05),(11.4,7.05),(11.4,6.05),(-2.3,6.05),(-2.3,-6.95),(-14.6,-6.95)])
    def arrow(x,y,angle):
        t=math.radians(angle);co,si=math.cos(t),math.sin(t)
        outline=[(-.12,-.66),(.12,-.66),(.12,.05),(.38,.05),(0,.67),(-.38,.05),(-.12,.05)]
        vs=[Vector((x+px*co-py*si,y+px*si+py*co,.0045)) for px,py in outline]
        poly('FloorMarkings',vs,triangles(vs),'FloorPaint')
    for x,y,a in [(-11,-9,-90),(-5,-9,-90),(0,-4,0),(0,1,0),(5,5,-90),(10.5,5,-90)]:arrow(x,y,a)
    # Bounded diagonal hatch at the exit, with no rack or label penetrating the wall.
    x0,x1,y0,y1=12.2,14.55,3.30,6.70
    stroke([(x0,y0),(x1,y0)],.065);stroke([(x0,y1),(x1,y1)],.065)
    for y in [y0+.20+i*.60 for i in range(9)]:
        # Clip ascending diagonals to the interior rectangle.
        lo=max(x0+.06,x0+(y0+.08-y));hi=min(x1-.06,x0+(y1-.08-y))
        if hi-lo>.1:stroke([(lo,y+lo-x0),(hi,y+hi-x0)],.09)
    # Inset load-bay corner marks stay away from the through route.
    for x0,y0,x1,y1 in [(-8.6,-3,-5.5,1.2),(5.3,-4.0,8.4,.1),(-8.6,4,-6.3,6.4)]:
        for x,sx in ((x0,1),(x1,-1)):
            for y,sy in ((y0,1),(y1,-1)):stroke([(x+sx*.45,y),(x,y),(x,y+sy*.45)],.08)
