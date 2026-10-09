"""Station-scale circular power hall, continuous annular gallery and control cabin.

All dimensions are authored in metres. This is production mesh authoring only.
The main ring is an actual open-centre deck, with individual convex UCX sectors.
"""
import math
from mathutils import Vector


def build_round_hall(g, cfg, atlas):
    s = next(r for r in cfg['rooms'] if r['id'] == 'AccumulatorControl')
    R, H = s['radius_m'], s['dimensions_m'][2]
    Z = s['upper_deck_m']
    RI, RO = R - 4.8, R - .48
    P = s['ports'][1]['position'][0]
    g.ROOM = s['id']

    def xy(r, a, z=None):
        p = (r * math.cos(a), r * math.sin(a))
        return (*p, z) if z is not None else p

    def ibeam(a, b, w=.30, h=.40):
        a, b = Vector(a), Vector(b)
        n, u, v = g.basis(b-a)
        g.beam('RoofFrame', a, b, .055, h, 'Paint')
        for q in (-1, 1):
            g.beam('RoofFrame', a+v*q*h/2, b+v*q*h/2, w, .034, 'Paint')

    # Circle has 96 true radial facets; the only straight registration faces
    # are the two short 3.5m portal chords, centred at the exact connector ends.
    a0 = math.asin(1.75/R)
    outline = []
    for a, b in [(a0, math.pi-a0), (math.pi+a0, math.tau-a0)]:
        for j in range(49):
            outline.append(xy(R, a+(b-a)*j/48))
    g.prism('Structure', outline, -.32, 0, 'Concrete', True)
    for i, a in enumerate(outline):
        b = outline[(i+1) % len(outline)]
        portal = abs(a[0]-b[0]) < 1e-5 and abs(abs(a[0])-P) < 1e-5
        g.wall(a, b, H, door=portal, thickness=.38)
    g.prism('Roof', outline, H, H+.34, 'Concrete', True)
    # Original straight ceramic groups sit on proper chord mortar beds rather
    # than floating off, stretching, or penetrating the curved perimeter.
    for deg in s.get('tile_panel_angles_deg', []):
        a=math.radians(deg);p=xy(R-.18,a)
        g.box('DadoBacking',(p[0],p[1],.72),(.26,4.12,1.44),'Concrete',a)

    # A coherent roof wheel has a central oculus-shaped coffer and 24 rafters.
    g.ring('RoofFrame', (0, 0, H-.28), (0, 0, 1), 5.12, 4.79, .36, 'Paint', 96)
    g.ring('RoofFrame', (0, 0, H-.47), (0, 0, 1), 5.18, 4.76, .07, 'Steel', 96)
    for i in range(24):
        a = (i+.5)*math.tau/24
        x, y = xy(R-.53, a)
        g.box('Structure', (x, y, (H-.50)/2), (.14, .42, H-.50), 'Paint', a, True)
        for d in (-.23, .23):
            g.box('Structure', (x-math.sin(a)*d, y+math.cos(a)*d, (H-.50)/2), (.50, .045, H-.50), 'Paint', a, True)
        g.box('Trim', (x, y, .085), (.72, .72, .17), 'Steel', a)
        for dx in (-.26, .26):
            for dy in (-.26, .26):
                g.bolt('Hardware', (x+dx, y+dy, .176), (0,0,1), .032)
        ibeam(xy(R-.58, a, H-.57), xy(4.98, a, H-.57))
        # Knee braces beneath the outer roof rim remain well above circulation.
        g.beam('RoofFrame', xy(R-.60, a, H-2.0), xy(R-2.10, a, H-.64), .15, .18, 'Paint')

    # Actual upper annulus: segmented mesh and matching convex sectors, no
    # filled centre/collision lid. 3.84m floor and 3.60m clear underside.
    N = 96
    stairs_a = [math.radians(a) for a in s.get('stairs_angles_deg',[225,315])]
    stair_half = s.get('stairs_width_m',2.0)/2+.025
    upper = bool(s.get('control_room',{}).get('floor_m'))
    for i in range(N):
        a, b = i*math.tau/N, (i+1)*math.tau/N
        quad = [xy(RI,a), xy(RO,a), xy(RO,b), xy(RI,b)]
        g.prism('GalleryDeck', quad, Z-.24, Z, 'Deck', True)
        # Narrow steel deck seams have finite separation from the deck skin.
        if i % 2 == 0:
            g.beam('Trim', xy(RI+.04,a,Z+.006), xy(RO-.04,a,Z+.006), .018, .008, 'Steel')
        # Clip at the exact stair guardrail boundaries, not whole deck sectors.
        # This avoids exposed shoulders beside a narrow stair in a wide gap.
        intervals=[(a,b)];half_mouth=math.asin(stair_half/(RI+.04))
        gaps=[(c-half_mouth,c+half_mouth) for c in stairs_a]
        if upper:
            edge=math.acos(10/(RI+.04));gaps.append((edge,math.pi-edge))
        for lo,hi in gaps:
            next_intervals=[]
            for aa,bb in intervals:
                if bb<=lo or aa>=hi:next_intervals.append((aa,bb))
                else:
                    if aa<lo:next_intervals.append((aa,lo))
                    if bb>hi:next_intervals.append((hi,bb))
            intervals=next_intervals
        for aa,bb in intervals:
            g.rail(xy(RI+.04,aa,Z), xy(RI+.04,bb,Z))
        # Outer railing is physically present against the outside service gap.
        g.rail(xy(RO-.05,a,Z), xy(RO-.05,b,Z))
    for i in range(24):
        a=(i+.5)*math.tau/24
        x,y=xy(RI+.30,a)
        g.box('Structure',(x,y,(Z-.42)/2),(.24,.24,Z-.42),'Paint',a,True)
        g.box('Trim',(x,y,.04),(.48,.48,.08),'Steel',a)
        ibeam(xy(RI+.15,a,Z-.39),xy(RO-.15,a,Z-.39),.23,.28)
        g.beam('RoofFrame',xy(RI+.31,a,Z-1.15),xy(RI+1.20,a,Z-.38),.12,.14,'Paint')

    # Two generous radial stairs keep the centre aisle around the core open.
    if upper:
        import upper_control_geometry
        upper_control_geometry.platform(g,s,RI,Z,ibeam)
    count=round(Z/.16);rise=Z/count;going=.36;run=count*going;width=s.get('stairs_width_m',2.0)
    for a in stairs_a:
        n=Vector((math.cos(a),math.sin(a),0));t=Vector((-n.y,n.x,0))
        start=RI-run
        for i in range(count):
            top=(i+1)*rise-(.003 if i==count-1 else 0)
            p=n*(start+(i+.5)*going)
            g.box('Structure',(p.x,p.y,top/2),(going,width,top),'Concrete',a,True)
            p=n*(start+(i+.055)*going)
            g.box('Trim',(p.x,p.y,top+.004),(.025,width-.04,.008),'Yellow',a)
        for side in (-1,1):
            p=n*(start+.5*going)+t*side*(width/2+.025)
            q=n*(RI-.5*going)+t*side*(width/2+.025)
            g.rail((p.x,p.y,rise),(q.x,q.y,Z))
            end=n*math.sqrt((RI+.04)**2-stair_half**2)+t*side*stair_half
            g.rail((q.x,q.y,Z),(end.x,end.y,Z))
        p=n*(start-.95)
        g.box('Markings',(p.x,p.y,.009),(1.35,2.40,.009),'Yellow',a)

    # Broad foundation, service boundary, and meaningful radial cable trenches.
    g.prism('Structure',[xy(4.10,i*math.tau/48) for i in range(48)],0,.20,'Concrete',True)
    g.ring('Markings',(0,0,.011),(0,0,1),4.76,4.68,.008,'Yellow',128)
    for a in (math.radians(45),math.radians(135)):
        n=Vector((math.cos(a),math.sin(a),0));t=Vector((-n.y,n.x,0))
        start,end=4.55,RI-.65
        mid=n*((start+end)/2)
        g.box('Trim',(mid.x,mid.y,.006),(end-start,.52,.012),'Dark',a)
        for j in range(math.ceil((end-start)/.14)):
            p=n*(start+(j+.5)*.14)
            g.box('Trim',(p.x,p.y,.024),(.027,.49,.026),'Deck',a)
        for side in (-1,1):
            p=n*start+t*side*.30;q=n*end+t*side*.30
            g.beam('Trim',(p.x,p.y,.025),(q.x,q.y,.025),.028,.035,'Steel')

    # Four wall service racks beneath the ring: load-bearing uprights, shelves,
    # bus enclosures and realistically terminated coolant/conduit connections.
    for i,a in enumerate(map(math.radians,(32,148,205,335))):
        n=Vector((math.cos(a),math.sin(a),0));t=Vector((-n.y,n.x,0));c=n*(R-1.24)
        for off in (-1.28,1.28):
            p=c+t*off
            g.box('Equipment',(p.x,p.y,1.44),(.09,.12,2.88),'Paint',a,True)
            g.box('Equipment',(p.x,p.y,.05),(.28,.30,.10),'Steel',a)
        for z in (.16,1.18,2.22,2.87):
            g.box('Equipment',(c.x,c.y,z),(.82,2.68,.09),'Deck',a,True)
        for j in (-1,0,1):
            p=c+t*j*.78
            g.box('Equipment',(p.x,p.y,.68),(.58,.61,.91),'Paint',a,True)
            q=p-n*.307
            g.beam('Equipment',(q.x,q.y,.31),(q.x,q.y,1.02),.035,.048,'Steel')
            for z in (1.53,1.83):
                p2=p-n*.10
                g.cylinder('Equipment',(p2.x,p2.y,z-.10),(p2.x,p2.y,z+.10),.20,'Ceramic',24)
        p=c-n*.45
        g.plate((p.x,p.y,2.56),1.3,.30,'MainBus' if i%2==0 else 'Cooling',(-n.x,-n.y,0),atlas)
        for j in (-1,1):
            p=c+t*j*.92+n*.44
            g.rounded_pipe('Pipework',[(p.x,p.y,.18),(p.x,p.y,3.04),(p.x+n.x*.58,p.y+n.y*.58,3.04)],.055,'Enamel',20)
            g.flange('Hardware',(p.x,p.y,1.50),(0,0,1),.055,8)

    if upper:
        upper_control_geometry.cabin(g,s,atlas)
    else:
        # Enclosed peripheral main control cabin. Real floor/wall/ceiling solids;
        # its separate ceiling remains below the continuous annular deck.
        room=s['control_room'];x0,x1=room['x_bounds_m'];front,back=room['y_bounds_m'];CH=room['height_m']
        width=x1-x0
        # Back and side walls, with two 1.5m ground-level personnel openings.
        g.box('ControlRoom',(0,back,CH/2),(width,.22,CH),'Concrete',collision=True)
        for x in (x0,x1):
            g.box('ControlRoom',(x,(front+back)/2,CH/2),(.22,back-front,CH),'Concrete',collision=True)
        doors=[x0+2.10,x1-2.10];half=.80
        intervals=[(x0,doors[0]-half),(doors[0]+half,doors[1]-half),(doors[1]+half,x1)]
        for lo,hi in intervals:
            g.box('ControlRoom',((lo+hi)/2,front,CH/2),(hi-lo,.24,CH),'Paint',collision=True)
        for x in doors:
            g.box('ControlRoom',(x,front,(2.44+CH)/2),(1.60,.24,CH-2.44),'Paint',collision=True)
            for side in (-1,1):
                g.box('ControlRoom',(x+side*.79,front,1.21),(.06,.32,2.42),'Steel',collision=True)
            g.box('ControlRoom',(x,front,2.43),(1.64,.32,.06),'Steel',collision=True)
        # Smoked inspection windows are physically closed recessed infill, backed
        # by solid wall for now; no unsupported new translucent shader is implied.
        for x in (-3.4,0,3.4):
            g.box('ControlRoom',(x,front-.145,1.98),(2.88,.045,1.13),'Steel')
            g.box('ControlRoom',(x,front-.174,1.98),(2.70,.014,.96),'Dark')
            for xx in (-.88,0,.88):
                g.box('ControlRoom',(x+xx,front-.188,1.98),(.026,.025,1.01),'Paint')
            for zz in (1.72,2.22):g.box('ControlRoom',(x,front-.190,zz),(2.72,.022,.022),'Paint')
        g.box('ControlRoom',(0,(front+back)/2,CH+.11),(width+.22,back-front+.25,.22),'Concrete',collision=True)
        # Interior cable trays, equipment rails and ventilation grilles.
        for x in (x0+.36,x1-.36):
            g.tray((x,front+.32),(x,back-.20),CH-.31,.28)
        for x in (-4.8,0,4.8):
            for j in range(13):g.box('ControlRoom',(x+(j-6)*.115,back-.136,2.70),(.052,.035,.27),'Steel')
        g.plate((0,front-.215,3.04),3.80,.62,'ControlRoom',(0,-1,0),atlas)
        for x in doors:g.plate((x,front+.175,2.80),1.35,.30,'Exit',(0,1,0),atlas)
    g.plate((0,-R+.60,4.90),5.5,1.12,'Accumulator',(0,1,0),atlas)
    for x in (-2.1,2.1):g.beam('Hardware',(x,-R+.20,4.90),(x,-R+.58,4.90),.09,.10,'Steel')
    da=math.radians(170);dp=xy(R-.40,da,2.15)
    g.plate(dp,1.8,.65,'Danger',(-math.cos(da),-math.sin(da),0),atlas)
    g.plate((P-.235,0,3.45),2.2,.62,'Exit',(-1,0,0),atlas)

    # Continuous high-level perimeter cable service, beneath roof and clear of
    # lamps/stair headroom; all supports terminate on actual circle structure.
    for i in range(48):
        a,b=i*math.tau/48,(i+1)*math.tau/48
        g.tray(xy(R-1.06,a),xy(R-1.06,b),H-1.12,.40)
        if i%2==0:
            p=xy(R-1.06,a,H-1.20);q=xy(R-.25,a,H-1.20)
            g.beam('Cablework',p,q,.055,.075,'Steel')
