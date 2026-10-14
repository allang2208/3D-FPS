"""Closed manufactured hardware; each fixture has real joints, recesses and support."""
import math
from mathutils import Vector,Matrix

def build(g,roles,atlas):
    def B(k,c,s,m='Brushed',col=False):g.box(k,c,s,m,collision=col)
    def ring(k,c,r,inner,depth=.008,m='Brushed'):g.ring(k,c,(0,-1,0),r,inner,depth,m,64)
    def bolt(k,c,r=.005,axis=(0,-1,0)):g.bolt(k,c,axis,r)
    def label(key,c,w,room=None):
        a=atlas['rects'][key];h=w*(a[3]-a[1])/(a[2]-a[0]);start=len(g.group('DetailPlates')['m'])
        g.printed_plate('DetailPlates',c,w,h,key,(0,-1,0),atlas,.004)
        payload=g.group('DetailPlates')
        for j in range(start,len(payload['m'])):
            if payload['m'][j]=='Labels':payload['m'][j]='DetailPrint'
    def outline(k,points,y0,y1,m):
        n=len(points);v=[(x,y,z) for y in (y0,y1) for x,z in points]
        f=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        g.poly(k,v,f,m)
    def frame(k,c,w,h,depth=.016,rail=.012,m='Brushed'):
        x,y,z=c
        for s in (-1,1):B(k,(x+s*(w-rail)/2,y,z),(rail,depth,h),m)
        for s in (-1,1):B(k,(x,y,z+s*(h-rail)/2),(w-2*rail,depth,rail),m)
    def hinge(k,x,y,z,h=.085):
        for i in range(5):
            a=z-h/2+i*h/5+.001;b=z-h/2+(i+1)*h/5-.001
            g.cylinder(k,(x,y,a),(x,y,b),.010,'Brushed',32)
            B(k,(x+(.017 if i%2 else -.017),y+.008,(a+b)/2),(.022,.010,b-a),'Brushed')
        g.cylinder(k,(x,y,z-h/2-.003),(x,y,z+h/2+.003),.0045,'Brushed',24)
        for s in (-1,1):bolt(k,(x+s*.019,y-.001,z+s*.022),.003)
    def shell(k,c,size,mat):
        x,y,z=c;w,d,h=size;t=.009
        B(k,(x,y+d/2-t/2,z),(w,t,h),mat)
        for s in (-1,1):B(k,(x+s*(w-t)/2,y,z),(t,d,h),mat)
        for s in (-1,1):B(k,(x,y,z+s*(h-t)/2),(w-2*t,d,t),mat)
    def gland(k,c,axis,r):
        g.lathe(k,c,axis,[(0,r*1.30),(.014,r*1.30),(.020,r),(.044,r),(.048,r*1.16),(.065,r*1.16),(.074,r*.78)],'Brushed',48)
        for z in (.026,.032,.038):g.ring(k,Vector(c)+Vector(axis)*z,axis,r*1.015,r*.94,.0025,'Brushed',48)
    # Staff mail cabinet: real slots, folded shell, small hinges, locks and label holders.
    g.ROOM='staff_living';k='MailSlots'
    for i,x in enumerate((-3.32,-2.72,-2.12)):
        shell(k,(x,-.325,.91),(.51,.24,.43),'Graphite')
        # Face frame surrounds an open posting slot. It has no hidden coplanar cover.
        B(k,(x,-.455,.859),(.477,.017,.283),'Graphite')
        B(k,(x,-.455,1.093),(.477,.017,.027),'Graphite')
        for s in (-1,1):B(k,(x+s*.226,-.455,1.04),(.025,.017,.078),'Graphite')
        frame(k,(x,-.465,.91),.494,.414,.014,.010)
        outline(k,[(x-.204,1.074),(x+.204,1.074),(x+.204,1.066),(x-.204,1.066)],-.495,-.446,'Brushed')
        B(k,(x,-.440,1.038),(.397,.004,.037),'Gasket')
        # Interior baffle is behind the slot; its bottom remains visibly recessed.
        B(k,(x,-.427,.998),(.411,.06,.009),'Graphite')
        for z in (.795,.979):hinge(k,x-.231,-.476,z,.072)
        g.cylinder(k,(x+.157,-.470,.790),(x+.157,-.482,.790),.020,'Brushed',64)
        ring(k,(x+.157,-.485,.790),.0205,.0152,.006)
        B(k,(x+.157,-.486,.790),(.003,.001,.014),'Gasket')
        frame(k,(x-.022,-.475,.908),.33,.087,.008,.009)
        label('mail'+str(i+1),(x-.022,-.481,.908),.309)
        for dx in (-.207,.207):
            for z in (.73,1.09):bolt(k,(x+dx,-.475,z),.004)
    label('mail',(-2.72,-.268,1.245),1.20)
    # Empty hooks mixed with cut brass keys and return tags.
    k='KeyRail';B(k,(-2.72,-.263,1.585),(1.70,.055,.060),'Brushed')
    for x in (-3.47,-1.97):bolt(k,(x,-.296,1.585),.006)
    for i in range(6):
        x=-3.42+i*.28
        g.tube(k,[(x,-.294,1.58),(x,-.374,1.58),(x,-.397,1.572),(x,-.413,1.593)],.0055,'Brushed',24)
        if i in (1,4):continue
        g.torus(k,(x,-.402,1.548),(0,1,0),.026,.0028,'Brushed',64,12)
        cx=x+.008;cz=1.514;start=len(g.group(k)['v'])
        # Bow is an actual hole, with a warded blade and individually cut teeth.
        ring(k,(cx,-.413,cz),.0175,.0105,.0024,'Brass')
        tooth=[(-.005,-.014),(.005,-.014),(.005,-.031),(.008,-.031),(.008,-.036),(.003,-.036),(.003,-.041),(.008,-.041),(.008,-.046),(.005,-.046),(.005,-.052),(.008,-.052),(.008,-.058),(-.005,-.058)]
        outline(k,[(cx+a,cz+b) for a,b in tooth],-.4142,-.4118,'Brass')
        B(k,(cx-.001,-.4145,cz-.035),(.0012,.0005,.039),'Brushed')
        angle=math.radians((-14,0,9,-7,0,15)[i]);rot=Matrix.Rotation(angle,3,'Y');pivot=Vector((x,-.413,1.548));payload=g.group(k)
        for j in range(start,len(payload['v'])):payload['v'][j]=tuple(pivot+rot@(Vector(payload['v'][j])-pivot))
        B(k,(x-.022,-.389,1.474),(.033,.006,.052),'Ivory')
        g.torus(k,(x-.022,-.393,1.510),(0,1,0),.011,.0016,'Brushed',40,10)
        for n in range(i+1):B(k,(x-.031+n*.003,-.3923,1.467),(.0014,.0006,.016),'Graphite')
    # Cylindrical lamps: hollow diffuser, solid end plugs seated inside its throat.
    for s in (-1,1):
        x=s*2.73;y=-.37;z=2.89;k='SconcePlate'
        B(k,(x,-.172,3.15),(.22,.08,.74),'Brushed')
        for zz in (2.84,3.46):bolt(k,(x,-.218,zz),.006)
        for zz in (2.98,3.32):g.cylinder(k,(x,-.208,zz),(x,-.37,zz),.014,'Brushed',48)
        profile=[(0,.089),(.025,.099),(.442,.099),(.467,.089),(.467,.083),(.442,.093),(.025,.093),(0,.083)]
        vs=[];fs=[];n=96
        for zz,r in profile:
            vs.extend((x+math.cos(i*math.tau/n)*r,y+math.sin(i*math.tau/n)*r,z+zz) for i in range(n))
        for j in range(len(profile)):
            for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i))
        g.poly('SconceShade',vs,fs,'Glow',smooth=True)
        for top in (False,True):
            base=3.357 if top else 2.867;direction=(0,0,1) if top else (0,0,-1)
            start=(x,y,base) if top else (x,y,2.890)
            g.lathe(k,start,direction,[(0,.079),(.006,.079),(.008,.111),(.019,.111),(.024,.106),(.025,.097)],'Brushed',96)
            zz=base+.026 if top else 2.864
            g.cylinder(k,(x,y,zz),(x,y,zz+(.005 if top else -.005)),.011,'Brushed',32)
    # Power distribution assembly retains its original footprint and cable route.
    g.ROOM='power';k='IsolatorCabinet';cx=-2.73
    shell(k,(cx,-.39,1.79),(1.56,.40,1.72),'PW')
    frame(k,(cx,-.594,1.79),1.535,1.695,.012,.012,'Gasket')
    B(k,(cx,-.614,1.79),(1.497,.027,1.654),'PW')
    frame(k,(cx,-.630,1.79),1.493,1.65,.013,.009,'Brushed')
    for z in (1.20,1.78,2.36):hinge(k,cx-.736,-.647,z,.15)
    for z in (1.34,2.23):
        g.cylinder(k,(cx+.64,-.638,z),(cx+.64,-.657,z),.025,'Brushed',64)
        B(k,(cx+.64,-.658,z),(.027,.001,.005),'Gasket')
    for x in (cx-.54,cx+.54):
        B(k,(x,-.16,1.79),(.08,.06,1.95),'Brushed')
        for z in (.91,2.68):bolt(k,(x,-.20,z),.013)
    for key,z,w in (('switch',2.36,1.16),('danger',1.10,1.12),('powerid',1.36,.77)):
        h=w*224/992;frame(k,(cx,-.637,z),w+.032,h+.024,.012,.012);label(key,(cx,-.646,z),w)
        for dx in (-w/2-.006,w/2+.006):bolt(k,(cx+dx,-.647,z),.004)
    # Rotary isolator with moulded grip, pointer, padlock hole and indexed bezel.
    k='HandleBezel'
    g.lathe(k,(cx,-.636,1.80),(0,-1,0),[(0,.214),(.018,.231),(.039,.231),(.047,.218)],'Graphite',128)
    g.ring(k,(cx,-.687,1.80),(0,1,0),.219,.180,.006,'Brushed',128)
    g.cylinder(k,(cx,-.686,1.80),(cx,-.710,1.80),.162,'Ivory',96)
    for i in range(13):
        a=math.radians(-60+i*10);r=.196
        g.beam(k,(cx+math.sin(a)*r,-.694,1.80+math.cos(a)*r),(cx+math.sin(a)*(r-.013),-.694,1.80+math.cos(a)*(r-.013)),.0025,.0015,'Graphite')
    g.lathe(k,(cx,-.715,1.80),(0,-1,0),[(0,.099),(.019,.099),(.038,.081),(.067,.081)],'SafetyRed',96)
    grip=[(cx-.030,1.72),(cx-.044,1.75),(cx-.044,1.985),(cx-.032,2.006),(cx+.032,2.006),(cx+.044,1.985),(cx+.044,1.75),(cx+.030,1.72)]
    outline(k,grip,-.863,-.786,'SafetyRed')
    B(k,(cx,-.866,1.90),(.042,.008,.148),'Gasket')
    for z in (1.855,1.878,1.901,1.924,1.947):B(k,(cx,-.871,z),(.040,.003,.006),'Graphite')
    g.ring(k,(cx+.132,-.779,1.71),(0,1,0),.024,.011,.016,'SafetyRed',48)
    label('off',(cx,-.702,1.585),.37)
    k='PorcelainBushings'
    for index,x in enumerate((-3.21,-2.73,-2.25)):
        B(k,(x,-.36,2.675),(.225,.225,.046),'Brushed')
        for dx in (-.076,.076):
            for dy in (-.076,.076):bolt(k,(x+dx,-.36+dy,2.701),.008,(0,0,1))
        gland(k,(x,-.36,2.703),(0,0,1),.065)
        profile=[(0,.051),(.015,.057)]
        for j in range(5):
            for q in range(1,21):
                t=q/20;profile.append((.015+(j+t)*.081,.055+.047*(math.sin(math.pi*t)**1.35)))
        profile += [(.433,.055),(.451,.048)]
        g.lathe(k,(x,-.36,2.790),(0,0,1),profile,'Porcelain',96)
        gland(k,(x,-.36,3.241),(0,0,1),.051)
        B(k,(x,-.36,3.339),(.120,.098,.032),'Brushed')
        B(k,(x,-.36,3.365),(.120,.098,.015),'Brushed')
        for dx in (-.039,.039):
            g.cylinder(k,(x+dx,-.36,3.326),(x+dx,-.36,3.397),.006,'Brushed',32)
            bolt(k,(x+dx,-.36,3.378),.011,(0,0,1))
        g.lathe(k,(x,-.36,3.392),(0,0,1),[(0,.038),(.04,.038),(.058,.030),(.15,.029)],'Gasket',64)
        for z in (3.423,3.443,3.463):g.ring(k,(x,-.36,z),(0,0,1),.039,.036,.007,'Gasket',64)
        # Phase bands remain above the terminal boot, without a second cable skin.
        g.ring(k,(x,-.36,3.57),(0,0,1),.0305,.029,.045,('SafetyRed','SafetyYellow','Brushed')[index],64)
    # Ground braid and connected cabinet underside cable glands.
    for x in (-3.14,-2.34):gland(k,(x,-.38,.93),(0,0,-1),.023)
    g.tube(k,[(-3.41,-.38,.96),(-3.41,-.38,.83),(-3.50,-.38,.78),(-3.57,-.26,.78)],.009,'EC',24)
    for z in (.86,.89,.92):g.ring(k,(-3.41,-.38,z),(0,0,1),.0096,.0085,.009,'SafetyYellow',32)
    # Maintenance bay, entirely between columns X=-7 and X=1.
    g.ROOM='Hall';k='MaintenancePanel'
    # Left: recognizable small electrical board with breakers and covered cable outlets.
    shell(k,(-5.45,-17.86,1.81),(.90,.22,.82),'Teal')
    B(k,(-5.45,-17.725,1.81),(.86,.022,.78),'Graphite')
    for i in range(6):
        x=-5.78+i*.132;B(k,(x,-17.696,1.73),(.109,.040,.26),'Ivory')
        B(k,(x,-17.661,1.75),(.067,.027,.092),'Graphite')
        B(k,(x,-17.641,1.747),(.057,.014,.038),'Brushed')
        for z in (1.625,1.840):g.cylinder(k,(x,-17.667,z),(x,-17.654,z),.009,'Brushed',24)
    for x in (-5.76,-5.14):gland(k,(x,-17.84,1.40),(0,0,-1),.027)
    # Centre: recessed pegboard, separated hand tools with their own hanging hooks.
    B(k,(-3.88,-17.887,1.80),(1.75,.13,1.18),'Teal')
    B(k,(-3.88,-17.808,1.80),(1.69,.020,1.12),'Graphite')
    for ix in range(14):
        for iz in range(9):g.cylinder(k,(-4.65+ix*.119,-17.792,1.32+iz*.118),(-4.65+ix*.119,-17.787,1.32+iz*.118),.011,'Gasket',16)
    # Three spanners, two screwdrivers, pliers: correct silhouettes and distinct handles.
    for i,x in enumerate((-4.45,-4.18,-3.91)):
        z=1.95-i*.04;length=.33+i*.045
        B(k,(x,-17.734,z-length/2),(.032,.025,length),'Brushed')
        g.ring(k,(x,-17.734,z),(0,1,0),.054,.032,.024,'Brushed',48)
        # Open jaw at the lower end, visibly separated prongs.
        B(k,(x,-17.734,z-length),(.084,.024,.023),'Brushed')
        for s in (-1,1):B(k,(x+s*.031,-17.734,z-length-.033),(.022,.024,.055),'Brushed')
    for i,x in enumerate((-3.57,-3.31)):
        g.lathe(k,(x,-17.73,1.57),(0,0,1),[(0,.023),(.018,.031),(.14,.031),(.17,.023)],'SafetyRed' if i else 'Ivory',48)
        g.cylinder(k,(x,-17.73,1.74),(x,-17.73,2.03),.006,'Brushed',24)
        for dx in (-.015,.015):B(k,(x+dx,-17.703,1.655),(.006,.004,.095),'Gasket')
    for i,x in enumerate((-4.45,-4.18,-3.91)):
        z=1.965-i*.04;g.tube(k,[(x,-17.80,z),(x,-17.724,z),(x,-17.719,z+.02)],.006,'Brushed',16)
    for x in (-3.57,-3.31):
        for s in (-1,1):g.tube(k,[(x+s*.022,-17.80,1.718),(x+s*.022,-17.73,1.718),(x+s*.022,-17.70,1.724)],.004,'Brushed',16)
    # Right: desk intercom with handset, keypad, grille and coiled lead.
    B(k,(-2.22,-17.844,1.82),(.62,.21,.88),'Ivory')
    B(k,(-2.22,-17.718,1.82),(.57,.025,.83),'Graphite')
    for i in range(12):B(k,(-2.11,-17.701,2.04+i*.012),(.25,.009,.004),'Gasket')
    for r in range(4):
        for c in range(3):B(k,(-2.22+c*.060,-17.678,1.85-r*.054),(.047,.018,.038),'Ivory')
    g.tube(k,[(-2.42,-17.64,1.54),(-2.44,-17.60,1.59),(-2.44,-17.60,2.08),(-2.42,-17.64,2.13)],.035,'Gasket',32)
    for z in (1.57,2.10):g.cylinder(k,(-2.42,-17.62,z),(-2.42,-17.56,z),.058,'Graphite',48)
    lead=[(-2.44+.024*math.cos(i*.6),-17.69+.024*math.sin(i*.6),1.52-i*.0016) for i in range(160)]
    g.tube(k,lead,.0035,'Gasket',12)
    # Hall-facing print normals are +Y (flip each newly authored plate as a rigid part).
    for key,c,w in [('panel',(-5.45,-17.70,2.10),.73),('tools',(-3.88,-17.789,2.30),1.46),('comms',(-2.22,-17.697,2.195),.49)]:
        start=len(g.group('DetailPlates')['v']);label(key,c,w);p=g.group('DetailPlates')
        for i in range(start,len(p['v'])):
            x,y,z=p['v'][i];p['v'][i]=(2*c[0]-x,2*c[1]-y,z)
    # Clear working bench: four legs and a lower shelf; its toolbox anchors move with it.
    k='ServiceBench';B(k,(-3.9,-17.23,.81),(5.05,.95,.08),'Wood',True)
    for x in (-6.25,-4.7,-3.1,-1.55):
        for y in (-17.59,-16.88):B(k,(x,y,.405),(.06,.06,.81),'Brushed',True)
    B(k,(-3.9,-17.23,.20),(4.96,.81,.032),'Graphite',True)
