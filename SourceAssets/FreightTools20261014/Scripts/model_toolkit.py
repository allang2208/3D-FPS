"""Open service case with independently authored tools, fitted foam, catches and hinges."""
import math
from mathutils import Matrix
import geometry as H

def socket(name,p,r=.78,height=2.3,drive_half=.3175):
    n=72;vs=[];fs=[]
    # Polygonal six point bore has straight internal flats and a beveled entry lip.
    rings=[(-height/2,r*.88,0),(-height/2+.09,r,0),(height/2-.09,r,0),
           (height/2,r*.93,0),(height/2,r*.60,6),(height/2-.11,r*.53,6)]
    drive_depth=min(1.4,height*.4)
    rings += [(-height/2+drive_depth,r*.53,6),(-height/2+drive_depth,drive_half,4),(-height/2,drive_half,4)] if height>.8 else [(-height/2,r*.53,6)]
    for z,rad,polygon in rings:
        for j in range(n):
            t=j*2*math.pi/n
            radius=rad/math.cos((t+math.pi/polygon)%(2*math.pi/polygon)-math.pi/polygon) if polygon else rad
            vs.append((p[0]+radius*math.cos(t),p[1]+radius*math.sin(t),p[2]+z))
    for i in range(len(rings)):
        for j in range(n):k=(j+1)%n;fs.append((i*n+j,i*n+k,((i+1)%len(rings))*n+k,((i+1)%len(rings))*n+j))
    o=H.mesh(name,vs,fs,'steel',True)
    for face in list(o.data.polygons)[3*n:]:face.use_smooth=False
    if height>.8:H.ring(name+' machined grip groove',(p[0],p[1],p[2]-.55),r*1.005,r*.98,.06,'blacksteel')
    return o

def spanner(x,y,z,length,number):
    jaw_scale=float(number)/10
    handle=[(x-.40,y-length*.36),(x-.57,y-length*.20),(x-.44,y+length*.25),(x-.38,y+length*.36),
            (x+.38,y+length*.36),(x+.44,y+length*.25),(x+.57,y-length*.20),(x+.40,y-length*.36)]
    H.extrude('Combination spanner '+number+' forged shank',handle,z,.38,'satin',.07)
    c=y+length*.40
    jaw=[(-.45,-.85),(-.95,-.40),(-1.12,.25),(-.75,.95),(-.39,.64),(-.49,.07),(.49,.07),(.39,.64),(.75,.95),(1.12,.25),(.95,-.40),(.45,-.85)]
    H.extrude('Combination spanner '+number+' open jaw',[(x+a*jaw_scale,c+b) for a,b in jaw],z,.43,'steel',.045)
    socket('Combination spanner '+number+' ring end',(x,y-length*.40,z),float(number)/10/1.06,.43)
    H.panel('Spanner '+number+' forged mark',(x,y,z+.205),.60,length*.32,'etch')
    H.stamp('Spanner size '+number,number,(x,c-.60,z+.23),.25,'blacksteel')

def ratchet(x,y,z):
    H.extrude('Ratchet forged tapered neck',[(x-.36,y-4.5),(x-.50,y+3.7),(x+.50,y+3.7),(x+.36,y-4.5)],z,.59,'steel',.09)
    H.loft('Ratchet contoured grip',[(z-.43,1.44,6.7,.65,x,y-4.4),(z,1.60,6.9,.70,x,y-4.4),(z+.43,1.44,6.7,.65,x,y-4.4)],'rubber')
    for j in range(12):H.rounded('Ratchet handle grip band',(x,y-7.2+j*.47,z+.40),(1.25,.13,.085),'teal',.05,.018)
    H.rounded('Ratchet pear head',(x,y+5.1,z),(2.65,3.25,.85),'steel',1.1,.09)
    H.cylinder('Ratchet head inset plate',(x,y+5.45,z+.46),1.04,.10,'blacksteel')
    H.cylinder('Ratchet quick release button',(x,y+5.45,z+.59),.45,.20,'satin')
    H.rounded('Ratchet reversible pawl lever',(x,y+4.38,z+.62),(.94,.40,.18),'blacksteel',.16,.025)
    H.box('Ratchet quarter inch square drive',(x,y+5.45,z-.66),(.635,.635,.65),'steel',.045)
    for side in (-1,1):H.screw('Ratchet cover fastener',(x+side*.82,y+4.79,z+.48),.12)

def screwdriver(x,y,z,length=15,small=False):
    start=len(H.PARTS);grip=length*.43;radius=.44 if small else .63
    H.lathe('Driver shaped handle',(0,0,0),[(-length*.48,radius*.57),(-length*.44,radius),(-length*.14,radius*.93),
             (-length*.08,radius*.68),(-length*.03,radius*.73),(0,radius*.73),(0,.13),(-length*.48,.13)],'teal',segments=64)
    for j in range(8):
        t=j*math.pi/4
        H.cord('Driver molded longitudinal grip',[(math.cos(t)*radius*.93,math.sin(t)*radius*.93,q) for q in (-length*.4,-length*.30,-length*.18)],.055,'rubber')
    H.cylinder('Driver rotating end cap',(0,0,-length*.49),radius*.80,.28,'blacksteel',edge=.05)
    H.cylinder('Driver steel shank',(0,0,length*.19),.15 if small else .21,length*.40,'steel')
    H.extrude('Driver flattened bit',[(-.19,length*.36),(-.20,length*.50),(.20,length*.50),(.19,length*.36)],0,.075,'blacksteel',.012)
    # The blade is made in XY above; reorient it into the same long axis as the shank.
    blade=H.PARTS[-1];blade.rotation_euler[0]=math.pi/2
    H.transform_since(start,Matrix.Translation((x,y,z))@Matrix.Rotation(-math.pi/2,4,'X'))

def pliers(x,y,z,needle=True):
    start=len(H.PARTS);tail=6.4 if needle else 5.3;head=4.9 if needle else 2.9
    for side in (-1,1):
        shape=[(side*.19,-.4),(side*.49,-1.5),(side*1.15,-3.4),(side*1.45,-tail),
               (side*1.90,-tail+.13),(side*1.70,-3.1),(side*.93,-1.0),(side*.62,.5)]
        H.extrude('Pliers forged handle tang',shape,z,.42,'satin',.08)
        H.cord('Pliers dual injection comfort grip',[(side*.94,-2.0,z),(side*1.47,-3.7,z),(side*1.65,-tail+.5,z)],.38,'teal')
        for j in range(6):H.cord('Pliers grip thumb texture',[(side*1.08,-2.4-j*.42,z+.29),(side*1.65,-2.4-j*.42,z+.30)],.045,'rubber')
        if needle:
            shape=[(side*.15,.35),(side*.79,.55),(side*.59,1.7),(side*.24,head),(side*.085,head),(side*.12,1.3)]
        else:
            shape=[(side*.12,.3),(side*1.03,.6),(side*1.16,1.55),(side*.40,head),(side*.09,head-.15),(side*.12,1.0)]
        H.extrude('Pliers machined jaw',shape,z+.03,.52,'steel',.045)
        if needle:
            for j in range(15):H.box('Needle jaw gripping tooth',(side*.16,1.1+j*.22,z+.28),(.20,.075,.07),'blacksteel',.012)
        else:H.extrude('Diagonal cutter ground edge',[(side*.10,1.0),(side*.10,head-.15),(side*.35,head-.10),(side*.35,1.0)],z+.32,.035,'satin',.005)
    H.cylinder('Pliers pivot rivet',(0,0,z+.34),.54,.18,'steel');H.cylinder('Pliers pivot centre',(0,0,z+.44),.16,.05,'blacksteel')
    H.transform_since(start,Matrix.Translation((x,y,0)))

def build():
    H.loft('Case base molded pan',[(0,29.2,20.2,1.55,0,0),(.35,30.0,21,1.65,0,0),(1.1,30,21,1.65,0,0)],'teal',16)
    H.frame('Case base structural sidewall',(0,0,2.9),(30,21,4.1),.68,'teal',1.65)
    H.frame('Case sealing rim',(0,0,5.02),(29.6,20.6,.28),.31,'rubber',1.45)
    # Cut foam has a crisp knife-cut lip. A global metal-style bevel at intersecting
    # pocket cuts produced microscopic sliver strips; retain the authored round pockets.
    foam=H.rounded('Base fitted foam insert',(0,0,3.1),(28.35,19.35,3.8),'foam',1.0,0)
    for x,w,l in ((-10,3.15,16.5),(-5.8,2.60,15.0),(-1.8,2.60,13.0),(2.2,2.60,11.0)):
        H.cut(foam,(x,-.2,4.4 if x==-10 else 4.8),(w,l,2.0 if x==-10 else 1.10),.95)
        # Finger scoops are real holes in the upper foam surface.
        H.cut(foam,(x,0,4.75),(w+.85,2.4,.75),.60)
    H.rounded('Ratchet shaped handle support',(-10,-4.4,3.70),(2.4,6.0,.60),'foam',.70,.06)
    ratchet(-10,0,4.4)
    for x,l,num in ((-5.8,13.7,'10'),(-1.8,11.7,'08'),(2.2,9.7,'06')):spanner(x,-.2,4.48,l,num)
    for col,x in enumerate((6.5,10.4)):
        for row,y in enumerate((-6.3,-2.1,2.1,6.3)):
            number=(6,7,8,9,10,12,13,14)[col*4+row];r=number/10/1.06
            H.cut(foam,(x,y,4.625),(r*2+.28,r*2+.28,2.35),r)
            socket('Drive socket '+str(number),(x,y,4.53),r,2.1)
            H.stamp('Foam socket size '+str(number),str(number),(x,y-1.37,5.018),.30,'white')
    # Lid is authored flat, then moved as a complete assembly about its physical hinge line.
    lid_start=len(H.PARTS)
    H.rounded('Lid molded outside',(0,0,-.48),(30,21,1.10),'teal',1.65,.10)
    H.frame('Lid raised wall',(0,0,.36),(30,21,1.40),.65,'teal',1.65)
    H.frame('Lid sealing lip',(0,0,1.07),(29.55,20.55,.19),.28,'rubber',1.40)
    lidfoam=H.rounded('Lid fitted foam insert',(0,0,.52),(28.3,19.3,1.65),'foam',1.0,0)
    for x,w,l in ((-9.6,4.25,13.8),(-3.4,4.25,11.7),(3.0,2.0,16.2),(8.4,1.8,13.6)):
        floor=.80 if x<0 else .50 if x==3.0 else .66
        H.cut(lidfoam,(x,-.1,(2.0+floor)/2),(w,l,2.0-floor),.65)
    pliers(-9.6,1.2,1.20,True);pliers(-3.4,.5,1.20,False)
    screwdriver(3.0,0,1.13,15.4);screwdriver(8.4,.5,1.13,12.4,True)
    for x in (-9.6,-3.4):
        start=len(H.PARTS)
        ribbon=[(-2.15,1.34),(-1.92,1.36),(-1.6,1.63),(0,1.67),(1.6,1.63),(1.92,1.36),(2.15,1.34),
                (2.15,1.43),(1.92,1.45),(1.6,1.72),(0,1.76),(-1.6,1.72),(-1.92,1.45),(-2.15,1.43)]
        H.extrude('Bent elastic retaining strap',ribbon,0,.72,'fabric',.025)
        H.transform_since(start,Matrix.Translation((x,-2.8,0))@Matrix.Rotation(math.pi/2,4,'X'))
        for dx in (-2.0,2.0):H.cylinder('Strap rivet',(x+dx,-2.8,1.48),.12,.05,'blacksteel')
    for x in (3.0,8.4):H.rounded('Driver retention band',(x,3.2,1.41),(1.65,.57,.13),'fabric',.07,.025)
    H.rounded('Eight piece bit rail',(4.25,-8.65,1.45),(12.4,1.0,.42),'orange',.25,.05)
    for j in range(8):
        x=-1+j*1.5
        H.cylinder('Driver bit hexagonal shank',(x,-8.65,1.88),.22,.68,'satin',sides=6,edge=.018)
        H.cylinder('Driver bit tapered working end',(x,-8.65,2.34),.14,.35,'blacksteel',sides=6 if j<4 else 4,edge=.015)
    H.panel('Lid original brand plate',(0,8.12,1.36),6.8,1.4,'badge')
    # Raised exterior reinforcing ribs remain visible from the back of the lid.
    for x in (-11,-6,6,11):H.rounded('Lid exterior reinforcing rib',(x,0,-1.08),(.42,16,.26),'teal',.15,.07)
    H.panel('Lid exterior serial plate',(0,0,-1.045),7.8,3.1,'serial','-Z')
    angle=math.radians(70)
    H.transform_since(lid_start,Matrix.Translation((0,10.5,5.0))@Matrix.Rotation(angle,4,'X')@Matrix.Translation((0,10.5,0)))
    # Knuckle hinges alternate across the two case halves, with a continuous steel pin.
    for x in (-9,9):
        for j in range(5):H.cylinder('Hinge knuckle',(x-1.2+j*.60,10.70,5.0),.40,.54,'teal' if j%2 else 'blacksteel','X')
        H.cylinder('Hinge pin',(x,10.70,5.0),.15,3.35,'steel','X')
    for x in (-9.4,9.4):
        H.rounded('Front latch foundation',(x,-10.69,3.32),(2.70,.58,2.35),'blacksteel',.35,.065)
        H.rounded('Latch locking paddle',(x,-11.08,3.32),(1.80,.30,1.72),'orange',.28,.045)
        H.cylinder('Latch pivot',(x,-11.05,2.43),.16,2.30,'steel','X')
    handle_start=len(H.PARTS)
    H.frame('Carry handle with real opening',(0,0,0),(10.1,3.9,.95),.72,'rubber',1.45)
    H.transform_since(handle_start,Matrix.Translation((0,-12.1,2.8))@Matrix.Rotation(math.pi/2,4,'X'))
    for x in (-4.4,4.4):
        H.box('Carry handle pivot bracket',(x,-10.8,2.8),(1.05,1.2,1.3),'teal',.20)
        H.cylinder('Carry handle pivot pin',(x,-11.2,2.8),.20,1.35,'steel','X')
    for x in (-13,13):
        for y in (-8,8):H.rounded('Case anti-slip foot',(x,y,-.13),(2.15,2.15,.40),'rubber',.50,.08)
    H.COLLISIONS.append(((0,0,2.65),(30,21,5.75)))
    H.COLLISIONS.append(((0,14.09,14.87),(30,21,2.5),('X',angle)))
