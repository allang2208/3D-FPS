"""Precise horticulture, sealed office and enlarged hydroponics room geometry."""
import math,random
def setup(host):
    for key in ('Vector','box','beam','poly','detail','root_tube','sign','cylinder','tank','valve','stairs','rail','wall_segment','rectangular_floor','benches','glazing'):
        globals()[key]=host[key]
    globals()['HOST']=host

def orient_new(snapshot,center,yaw):
    co,si=math.cos(yaw),math.sin(yaw)
    for key,g in HOST['G'].items():
        first=snapshot.get(key,0)
        for i in range(first,len(g['v'])):
            x,y,z=g['v'][i];x-=center[0];y-=center[1]
            g['v'][i]=(center[0]+x*co-y*si,center[1]+x*si+y*co,z)

def lathe(kind,x,y,z,profile,mat,sides=64,closed=False):
    vs=[(x+r*math.cos(j*math.tau/sides),y+r*math.sin(j*math.tau/sides),z+h) for r,h in profile for j in range(sides)]
    fs=[];uv=[]
    for i in range(len(profile) if closed else len(profile)-1):
        nxt=(i+1)%len(profile)
        for j in range(sides):
            fs.append((i*sides+j,i*sides+(j+1)%sides,nxt*sides+(j+1)%sides,nxt*sides+j))
            uv.append([(j/sides,profile[i][1]*3),((j+1)/sides,profile[i][1]*3),((j+1)/sides,profile[nxt][1]*3),(j/sides,profile[nxt][1]*3)])
    poly(kind,vs,fs,mat,uv,True)

def leaf(kind,start,end,width,mat='Leaf'):
    a,b=Vector(start),Vector(end);d=b-a;side=d.cross(Vector((0,1,.15))).normalized()
    vs=[]
    for i in range(9):
        t=i/8;w=width*math.sin(math.pi*t)**.8;p=a+d*t+Vector((0,0,math.sin(t*math.pi)*width*.35))
        vs.extend([p-side*w,p+Vector((0,0,width*.10*math.sin(t*math.pi))),p+side*w])
    fs=[]
    for i in range(8):
        k=i*3;fs.extend([(k,k+3,k+4,k+1),(k+1,k+4,k+5,k+2)])
    poly(kind,vs,fs,mat,smooth=True)

def specimen_jar(x,y,z,scale,index):
    profile=[(.060,.004),(.069,.008),(.074,.019),(.075,.04),(.075,.19),(.074,.211),(.067,.228),(.049,.243),(.046,.255),(.046,.285),(.041,.285),(.041,.257),(.044,.249),(.063,.230),(.070,.210),(.071,.19),(.071,.034),(.067,.018),(.059,.014)]
    lathe('SpecimenGlass',x,y,z,[(r*scale,h*scale) for r,h in profile],'JarGlass',64,True)
    cylinder('SpecimenGlass',(x,y,z+.008*scale),.060*scale,.012*scale,'JarGlass',48)
    # Sealing lip, gasket and knurled screw cap have distinct contact surfaces.
    detail.torus((x,y,z+.276*scale),(0,0,1),.046*scale,.003*scale,'SpecimenCaps','DarkPlastic',48)
    cylinder('SpecimenCaps',(x,y,z+.297*scale),.050*scale,.027*scale,'DarkPlastic',64)
    cylinder('SpecimenCaps',(x,y,z+.312*scale),.048*scale,.004*scale,'BareSteel',64)
    for j in range(40):
        a=j*math.tau/40
        beam('SpecimenCaps',(x+math.cos(a)*.050*scale,y+math.sin(a)*.050*scale,z+.287*scale),(x+math.cos(a)*.050*scale,y+math.sin(a)*.050*scale,z+.308*scale),.002*scale,.002*scale,'DarkPlastic')
    cylinder('SpecimenGel',(x,y,z+.058*scale),.069*scale,.085*scale,'JarGel',48)
    stem=[(x,y,z+.025*scale),(x-.009*scale,y,z+.105*scale),(x+.009*scale,y+.005*scale,z+.234*scale)]
    detail.tube('SpecimenContents',stem,.0024*scale,'Bark',12)
    for j in range(6):
        a=j*2.4+index;zz=z+(.084+j*.025)*scale
        end=(x+math.cos(a)*.053*scale,y+math.sin(a)*.053*scale,zz+.039*scale)
        detail.tube('SpecimenContents',[(x,y,zz),end],.0011*scale,'Bark',10)
        leaf('SpecimenContents',(x,y,zz),end,.011*scale)
    # A curved label with its own thickness; the image follows the bottle radius.
    atlas=HOST['ATLAS'];x0,y0,x1,y1=atlas['rects']['Seed'];aw,ah=atlas['size'];vs=[];fs=[];uv=[]
    for j in range(17):
        a=-math.pi/2-.88+1.76*j/16
        for zz in (.055,.088):vs.append((x+math.cos(a)*.076*scale,y+math.sin(a)*.076*scale,z+zz*scale))
    for j in range(16):
        fs.append((j*2,j*2+2,j*2+3,j*2+1));u0=(x0+(x1-x0)*j/16)/aw;u1=(x0+(x1-x0)*(j+1)/16)/aw
        uv.append([(u0,1-y1/ah),(u1,1-y1/ah),(u1,1-y0/ah),(u0,1-y0/ah)])
    poly('SpecimenLabels',vs,fs,'Labels',uv,True)

def frame_ring(kind,outer,inner,y0,y1):
    """One closed reveal ring, without intersecting boxes at the four corners."""
    def corners(bounds,y):
        x0,z0,x1,z1=bounds
        return [(x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1)]
    vertices=corners(outer,y0)+corners(inner,y0)+corners(outer,y1)+corners(inner,y1)
    faces=[]
    for i in range(4):
        j=(i+1)%4
        faces.extend([(i,j,4+j,4+i),(8+i,12+i,12+j,8+j),
            (j,i,8+i,8+j),(4+i,4+j,12+j,12+i)])
    HOST['poly'](kind,vertices,faces,'PaintedSteel')

def nursery(r):
    rectangular_floor(-13,-10,13,10)
    for x,y,angle in r['bench_positions']:
        snapshot={k:len(g['v']) for k,g in HOST['G'].items()};benches(x,y)
        if angle:orient_new(snapshot,(x,y),math.radians(angle))
    # One continuous front glazing, a closed head and sill, and a side entrance.
    box('OfficeWindowSill',(-10,3,.44),(6,.28,.88),'Concrete')
    box('Walls',(-10,3,3.335),(6,.28,.13),'Concrete')
    for x in (-12.895,-7.105):box('Walls',(x,3,2.075),(.21,.28,2.39),'Concrete')
    # Masonry jamb planes are x=-12.79/-7.21. The visible metal reveal
    # stands 20 mm inside the opening, instead of sharing those planes.
    # Rings share vertices at corners; facing strips meet the reveal at an
    # edge, without the coplanar corner patches of four overlapping boxes.
    frame_ring('WindowFrames',(-12.865,.88,-7.135,3.305),(-12.77,.95,-7.23,3.235),2.85,3.15)
    for ya,yb in ((2.836,2.85),(3.15,3.164)):
        frame_ring('OfficeTrim',(-12.89,.85,-7.11,3.34),(-12.76,.95,-7.24,3.24),ya,yb)
    wall_segment((-7,3),(-7,10),3.4,[dict(center=1.6,width=1.6,height=2.55)],tiles=False)
    box('PrepCanopy',(-10,6.5,3.52),(6.28,7.28,.24),'Concrete')
    # Lab bench, under-bench shelf, backsplash, electrical service and drying rack.
    lab_snapshot={k:len(g['v']) for k,g in HOST['G'].items()}
    box('Benches',(-10,9.17,.91),(3.5,1.12,.07),'BareSteel')
    box('Benches',(-10,9.56,1.04),(3.5,.05,.22),'BareSteel')
    for x in (-11.5,-8.5):
        for y in (8.73,9.57):
            box('Benches',(x,y,.44),(.055,.055,.88),'BareSteel');cylinder('Benches',(x,y,.027),.041,.05,'Rubber',24)
    box('Benches',(-10,9.2,.24),(3.3,.91,.035),'PaintedSteel')
    for x in (-11.3,-10.6,-9.9):box('OfficeSupplies',(x,9.2,.36),(.48,.42,.20),'Paper')
    for j,(x,y,s) in enumerate([(-11.3,9.16,.92),(-11.02,9.32,1.06),(-10.68,9.10,.86),(-10.4,9.34,.95),(-9.66,9.28,1.14),(-9.37,9.03,.94),(-8.99,9.31,.90),(-8.70,9.02,1.02)]):specimen_jar(x,y,.974,s,j)
    box('OfficeSupplies',(-10,9.17,.9615),(3.25,.80,.025),'DarkPlastic')
    box('OfficeBoard',(-12.81,5.1,1.72),(.06,1.2,.82),'PaintedSteel')
    for j in range(4):box('OfficeBoard',(-12.772,4.69+j*.25,1.70),(.009,.21,.57),'Paper')
    # The north structural columns project in front of the wall: keep the lab assembly clear.
    for key,g in HOST['G'].items():
        for i in range(lab_snapshot.get(key,0),len(g['v'])):
            x,y,z=g['v'][i];g['v'][i]=(x,y-.45,z)
    sign((-10,9.76,2.48),1.3,'Seed');sign((-6.845,6.2,2.25),.8,'Control',n=(1,0,0))
    # Both wall manifolds follow the back edge of the benches, branch into trays.
    tank('NutrientTank',10.4,-8.7)
    detail.smooth_pipe([(-5.5,-9.06,2.05),(9.45,-9.06,2.05),(9.45,-8.7,2.05),(9.65,-8.7,2.05)],.045)
    detail.smooth_pipe([(-5.5,9.06,2.05),(11.7,9.06,2.05),(11.7,2.3,2.05),(11.7,2.3,3.4),(11.7,-2.3,3.4),(11.7,-2.3,2.05),(11.7,-8.7,2.05),(11.25,-8.7,2.05)],.045)
    for x,y,_ in r['bench_positions']:
        back=1 if y>0 else -1
        detail.smooth_pipe([(x,back*9.06,2.05),(x,y+back*.53,2.05),(x,y+back*.53,1.04)],.016)
        beam('Services',(x,back*9.78,2.02),(x,back*9.06,2.02),.045,.06,'BareSteel')
        for dx in (-.94,0,.94):
            detail.tube('Services',[(x+dx,y+back*.59,1.07),(x+dx,y+back*.24,1.08),(x+dx,y+back*.24,1.01)],.007,'Rubber',12)
    valve((9.45,-8.7,2.05),(0,1,0))

def raft(cx,cy):
    kind='FloatingBeds';nx=8;ny=3;dx=.70;dy=.42;rad=.104;N=48
    for sx in (-3.02,3.02):
        box(kind,(cx+sx,cy,-.13),(.27,1.55,.50),'DarkPlastic')
        box(kind,(cx+sx,cy,.145),(.10,1.64,.10),'BareSteel')
        for yy in (-.60,.60):detail.fastener((cx+sx,cy+yy,.20),(0,0,1),.009,kind)
    for yy in (-.77,.77):box(kind,(cx,cy+yy,.11),(6.13,.10,.13),'BareSteel')
    for j in range(nx):
        for k in range(ny):
            x=cx+(j-3.5)*dx;y=cy+(k-1)*dy;vs=[]
            for z in (.005,.045):
                for inner in (False,True):
                    for q in range(N):
                        a=q*math.tau/N;co,si=math.cos(a),math.sin(a)
                        radius=rad if inner else min(dx/2/max(abs(co),1e-6),dy/2/max(abs(si),1e-6))
                        vs.append((x+co*radius,y+si*radius,z))
            fs=[]
            for q in range(N):
                q1=(q+1)%N
                fs.extend([(2*N+q,2*N+q1,3*N+q1,3*N+q),(q,N+q,N+q1,q1),(N+q,3*N+q,3*N+q1,N+q1)])
            poly(kind,vs,fs,'Ceramic')
            # Open net pot, visible drainage cage and separate growing medium.
            detail.ring((x,y,.057),(0,0,1),.110,.093,.024,'DarkPlastic',32,kind)
            detail.ring((x,y,-.16),(0,0,1),.073,.067,.018,'DarkPlastic',24,kind)
            for q in range(12):
                a=q*math.tau/12
                detail.tube(kind,[(x+.068*math.cos(a),y+.068*math.sin(a),-.16),(x+.099*math.cos(a),y+.099*math.sin(a),.05)],.004,'DarkPlastic',10)
            HOST['v4'].medium(x,y,.072,.089)
            if (j+k)%2==0:
                for m in range(3):
                    a=m*2.1+j;root_tube([(x,y,-.08),(x+.027*math.cos(a),y+.04*math.sin(a),-.31),(x+.07*math.cos(a+.4),y+.06*math.sin(a),-.67)],.008,.0018,'RootFibres',10)
    # A real service inlet and hose, tied to the outside supply manifold.
    x=cx+3.0
    detail.smooth_pipe([(x,cy+.7,.14),(x+.40,cy+.7,.14),(x+.40,cy+.7,.55)],.018)
    sign((cx,cy-.83,.17),.45,'Tray')

def hydro(r):
    # Only basins interrupt the finished slab. Bridge spans occupy those holes exclusively.
    for rect in [(-20,-15,20,-6),(-20,6,20,15),(-20,-6,-12,6),(-2,-6,2,6),(12,-6,20,6)]:rectangular_floor(*rect)
    for cx in (-7,7):
        box('PoolShell',(cx,0,-1.36),(10,12,.24),'Concrete')
        for x in (cx-5,cx+5):box('PoolShell',(x,0,-.74),(.18,11.64,1.04),'Concrete')
        for y in (-5.91,5.91):box('PoolShell',(cx,y,-.74),(10,.18,1.04),'Concrete')
        box('Water',(cx,0,-.42),(9.78,11.60,.012),'Water')
        box('Algae',(cx,0,-1.225),(9.74,11.58,.025),'Algae')
        for cy in (-3.8,3.8):raft(cx,cy)
        box('BridgeDecks',(cx,0,-.085),(10,3.1,.17),'BridgeDeck')
        for y in (-1.53,1.53):rail((cx-4.88,y,0),(cx+4.88,y,0))
        # Copings stop at the bridge mouths. There are no duplicate top faces at grade.
        for x in (cx-5,cx+5):
            for yy in (-3.81,3.81):box('PoolCoping',(x,yy,.035),(.28,4.34,.07),'BareSteel')
        for yy in (-6,6):box('PoolCoping',(cx,yy,.035),(9.72,.28,.07),'BareSteel')
        # Return steps ascend toward the outside dry floor, away from the basin interior.
        for j in range(6):
            top=-1.2+(j+1)*.2;yy=-4.08-j*.32
            box('PoolEscapeSteps',(cx,yy,(top-1.2)/2),(1.35,.32,top+1.2),'Concrete')
        for yy in (-.98,.98):box('BridgeBearers',(cx,yy,-.22),(10,.13,.21),'PaintedSteel')
        for xx in (cx-4.7,cx,cx+4.7):
            for yy in (-1.35,1.35):detail.fastener((xx,yy,.012),(0,0,1),.010,'DeckHardware')
    # Stairs are entirely on the 8 m side aprons; bottom landings have 2.3 m clear depth.
    box('Platforms',(0,11.85,2.29),(34.4,5.7,.22),'BridgeDeck')
    rail((-14.8,9,2.4),(14.8,9,2.4));rail((-17.2,14.7,2.4),(17.2,14.7,2.4))
    for x in (-16,16):
        stairs(x,3.4,2.4,2.4,5.6)
        rail((x+(-1.2 if x<0 else 1.2),9,2.4),(x+(-1.2 if x<0 else 1.2),14.7,2.4))
        for yy in (1.3,2.1):box('StairApproachMarkings',(x,yy,.003),(1.6,.075,.006),'Yellow')
    for x in (-16,-8,0,8,16):
        for y in (9.25,14.35):
            box('Columns',(x,y,1.08),(.20,.20,2.16),'PaintedSteel')
            box('Columns',(x,y,.035),(.44,.44,.07),'BareSteel')
        box('PlatformBearers',(x,11.85,2.12),(.15,5.7,.16),'PaintedSteel')
    for x in (-12,-8):tank('WaterTreatment',x,-12.7)
    for x in (4,8,12):pump_detail(x,-12.8)
    detail.smooth_pipe([(-12,-11.85,.96),(-12,-10.8,.96),(12.85,-10.8,.96),(12.85,-12.8,.96)],.095)
    detail.smooth_pipe([(-8,-11.85,2.9),(-8,-10.15,2.9),(18.6,-10.15,2.9),(18.6,-2.3,2.9),(18.6,-2.3,3.45),(18.6,2.3,3.45),(18.6,2.3,2.9),(18.6,5.5,2.9),(11.5,5.5,2.9),(11.5,5.5,-.26)],.075)
    detail.tube('Water',[(11.5,5.5,-.26),(11.5,5.5,-.43)],.025,'Water',24)
    for x in (4,8,12):
        detail.smooth_pipe([(x+.85,-12.8,.64),(x+.85,-10.8,.64),(x+.85,-10.8,.96)],.075)
        valve((x+.85,-11.65,.95),(0,1,0))
    for cx in (-7,7):
        detail.smooth_pipe([(cx+4.3,4.5,.55),(cx+4.3,2.0,.55),(cx+4.3,2.0,-.60),(cx+4.3,-2.0,-.60),(cx+4.3,-2.0,.55),(cx+4.3,-10.8,.55),(cx+4.3,-10.8,.96)],.024)
        for cy in (-3.8,3.8):
            detail.tube('Services',[(cx+3.4,cy+.7,.55),(cx+4.3,cy+.7,.55)],.024,'PipeEnamel',24)
    # Service screen, sampling sink and reagent shelf on the south maintenance wall.
    box('WaterControls',(-1.5,-14.72,1.55),(2.7,.15,1.1),'PaintedSteel')
    for x in (-2.35,-1.5,-.65):
        detail.tube('WaterControls',[(x,-14.60,1.67),(x,-14.55,1.67)],.12,'BareSteel',48)
        detail.tube('WaterControls',[(x,-14.547,1.67),(x,-14.54,1.67)],.104,'Ceramic',48)
        for j in range(9):
            a=math.pi*.18+j*math.pi*1.64/8
            beam('WaterControls',(x+math.cos(a)*.074,-14.531,1.67+math.sin(a)*.074),(x+math.cos(a)*.09,-14.531,1.67+math.sin(a)*.09),.004,.003,'DarkPlastic')
        beam('WaterControls',(x,-14.525,1.67),(x-.055,-14.525,1.72),.006,.004,'Yellow')
        for j in range(2):cylinder('WaterControls',(x-.12+j*.24,-14.535,1.27),.026,.025,'Rubber',20)
    sign((-.9,-14.60,2.28),1.3,'Filter',n=(0,1,0));sign((0,8.94,3.12),1.1,'Warning')

def pump_detail(x,y):
    HOST['pump']('WaterPumps',x,y)
    # Terminal box, gland, fan cover, foot brackets and a connected motor supply.
    box('WaterPumps',(x-.28,y,.92),(.32,.30,.16),'PaintedSteel')
    for dx in (-.12,.12):
        for dy in (-.10,.10):detail.fastener((x-.28+dx,y+dy,1.008),(0,0,1),.006,'WaterPumps')
    detail.tube('Services',[(x-.3,y-.17,.92),(x-.3,y-.48,.92),(x-.7,y-.53,.34),(x-.7,y-1.4,.34)],.012,'Rubber',16)
    detail.ring((x-.61,y,.64),(1,0,0),.25,.16,.03,'BareSteel',48,'WaterPumps')
