"""Original service meter: molded shells, working-form terminals, leads and rear service parts."""
import math
from mathutils import Matrix
import geometry as H

def digit(x,y,z,value):
    on={'0':'abcdef','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgecd','7':'abc','8':'abcdefg','9':'abfgcd'}[value]
    pos={'a':(0,.62,.60,.10),'g':(0,0,.60,.10),'d':(0,-.62,.60,.10),
         'f':(-.34,.31,.10,.48),'b':(.34,.31,.10,.48),'e':(-.34,-.31,.10,.48),'c':(.34,-.31,.10,.48)}
    for k,(dx,dy,w,h) in pos.items():
        if k in on:H.rounded('LCD seven segment '+k,(x+dx,y+dy,z),(w,h,.014),'lcdink',.035,.003)

def probe(x,red):
    start=len(H.PARTS);color='red' if red else 'rubber'
    H.lathe('Probe insulated handle',(0,0,0),[(-5,.16),(-4.5,.21),(-4,.29),(-.7,.31),(-.4,.38),(-.15,.38),(0,.25),(2.4,.18),(2.65,.15),(2.65,.08),(-5,.08)],color,segments=64)
    H.lathe('Probe touch guard',(0,0,0),[(-.50,.37),(-.44,.58),(-.24,.58),(-.18,.37)],color,segments=64)
    H.lathe('Probe stainless needle',(0,0,0),[(2.6,.09),(4.45,.09),(4.8,.008),(2.6,.008)],'steel',segments=48)
    for i in range(9):H.ring('Probe grip rib',(0,0,-3.6+i*.31),.322,.29,.10,color,sides=48)
    for i in range(6):H.ring('Probe strain relief',(0,0,-4.5-i*.16),.205-i*.008,.13,.07,color,sides=40)
    H.transform_since(start,Matrix.Translation((x,1.5,1.28))@Matrix.Rotation(-math.pi/2,4,'X'))
    H.COLLISIONS.append(((x,1.3,1.3),(.9,10.7,1.1)))

def build():
    # Waist, shoulder and end-cap radii are independent, so the rubber boot is not a rounded brick.
    H.loft('Protective overmold rear',[(.15,8.3,18.7,1.3,0,0),(.35,9.2,19.6,1.65,0,0),
         (.95,9.3,19.7,1.65,0,0),(2.4,9.0,19.4,1.45,0,0),(3.6,8.8,19.2,1.3,0,0)],'orange',16)
    H.loft('Housing perimeter gasket',[(2.90,8.64,18.7,1.35,0,0),(3.05,8.64,18.7,1.35,0,0)],'rubber',16)
    H.loft('Front injection molded housing',[(3.05,8.45,18.55,1.2,0,0),(3.65,8.35,18.45,1.18,0,0),
         (3.90,7.95,18.08,1.00,0,0)],'plastic',16)
    H.panel('Silkscreen faceplate',(0,0,3.912),7.45,17.1,'front')
    for side in (-1,1):
        for i in range(11):
            y=-5.5+i*.92
            rib=H.rounded('Rubber side grip scallop',(side*4.43,y,2.23),(.34,.46,1.92),'rubber',.14,.055)
            rib.rotation_euler[0]=side*.12
        H.rounded('Side probe retainer upper',(side*4.62,3.5,1.26),(.65,.85,1.15),'orange',.20,.06)
        H.rounded('Side probe retainer lower',(side*4.62,-2.8,1.26),(.65,.85,1.15),'orange',.20,.06)
    H.rounded('Display gasket',(0,4.65,3.99),(6.95,4.17,.22),'rubber',.43,.035)
    H.frame('Raised display bezel',(0,4.65,4.15),(6.8,4.05,.38),.26,'plastic',.4)
    H.rounded('Recessed display lens',(0,4.65,4.16),(6.29,3.54,.065),'screen',.17,.015)
    H.panel('LCD symbols and bar graph',(0,4.65,4.199),5.94,3.20,'lcd')
    for i in range(4):digit(-1.85+i*1.10,4.65,4.22,'0')
    H.cylinder('Decimal point',(-1.28,4.0,4.225),.065,.016,'lcdink',sides=24,edge=0)
    for x,text in ((-2.3,'HOLD'),(0,'RANGE'),(2.3,'SELECT')):
        H.rounded('Button recessed socket '+text,(x,1.4,3.99),(1.67,.77,.18),'rubber',.28,.04)
        H.rounded('Sealed rubber button '+text,(x,1.4,4.15),(1.43,.58,.30),'orange' if x==0 else 'plastic',.22,.04)
        H.stamp('Button legend '+text,text,(x,1.4,4.31),.17)
    H.panel('Selector scale',(0,-2.2,3.928),5.75,5.75,'scale')
    H.cylinder('Selector mounting recess',(0,-2.2,4.02),1.75,.19,'rubber',sides=96)
    H.lathe('Rotary selector crown',(0,-2.2,4.07),[(0,1.48),(.12,1.59),(.40,1.59),(.57,1.42),(.64,1.18),(.64,.01),(0,.01)],'plastic',segments=96)
    for j in range(32):
        t=j*2*math.pi/32
        o=H.rounded('Rotary selector traction flute',(1.52*math.cos(t),-2.2+1.52*math.sin(t),4.40),(.13,.22,.33),'rubber',.045,.02);o.rotation_euler[2]=t
    H.rounded('Selector finger bridge',(0,-2.2,4.85),(.72,2.53,.50),'plastic',.30,.10)
    H.extrude('Selector orange pointer',[(-.22,-.90),(0,-.54),(.22,-.90)],5.12,.025,'orange',.015)
    for x,color,name in ((-2.4,'red','10 A'),(0,'rubber','COM'),(2.4,'red','V OHM')):
        H.ring('Recessed insulated input '+name,(x,-6.70,4.03),.54,.27,.35,color)
        H.ring('Metal input ferrule '+name,(x,-6.70,3.98),.275,.195,.26,'gold')
        H.cylinder('Input bore floor '+name,(x,-6.70,3.65),.20,.035,'rubber',sides=40)
    # Two banana connectors occupy COM and voltage; the fused current socket stays visibly hollow.
    for x,color in ((0,'rubber'),(2.4,'red')):
        H.cylinder('Plug collar',(x,-6.70,4.28),.31,.47,color)
        H.rounded('Right angle banana plug',(x,-7.12,4.49),(.65,1.32,.52),color,.25,.06)
        for j in range(5):H.cylinder('Plug cable relief',(x,-7.65-j*.14,4.47),.18-j*.011,.08,color,'Y',32,.012)
    probe(-5.70,False);probe(5.70,True)
    H.cord('Black silicone test lead',[(0,-8.3,4.45),(0,-9.45,4.45),(0,-10.10,4.10),(-.3,-11.0,2.1),(-3.8,-11.3,.72),(-6.9,-8.6,.67),(-7.1,-4.1,.7),(-7.6,1.5,.65),(-6.9,6.4,.71),(-5.8,8.5,.72),(-4.9,7.1,.78),(-5.4,.5,.75),(-5.7,-3.7,1.28)],.10,'rubber')
    H.cord('Red silicone test lead',[(2.4,-8.3,4.45),(2.5,-9.45,4.50),(2.8,-10.25,3.9),(4.0,-10.8,2.3),(6.7,-10.4,.62),(7.3,-5.7,.65),(8.0,.8,.65),(7.6,6.3,.70),(6.3,8.6,.74),(5.1,7.3,.81),(5.2,1,.82),(5.7,-3.7,1.28)],.10,'red')
    # Serviceable rear face and folded stand, made even though the pickup normally lies face up.
    H.rounded('Rear battery door gasket',(0,-2.7,.09),(5.60,7.7,.15),'rubber',.48,.02)
    H.rounded('Rear battery cover',(0,-2.7,-.015),(5.30,7.40,.14),'plastic',.42,.035)
    H.panel('Rear safety and serial label',(0,3.6,.125),5.8,2.5,'serial','-Z')
    H.frame('Folded rear kickstand',(0,-.1,-.16),(6.6,13.8,.35),.48,'plastic',.75)
    for x in (-2.9,2.9):H.cylinder('Kickstand hinge pin',(x,6.4,.04),.23,.55,'steel','X')
    for x in (-3.3,3.3):
        for y in (-7.2,7.2):
            s=len(H.PARTS);H.screw('Rear housing recessed fastener',(0,0,0),.19)
            H.transform_since(s,Matrix.Translation((x,y,.17))@Matrix.Rotation(math.pi,4,'X'))
    H.COLLISIONS.append(((0,0,2.45),(9.25,19.5,5.25)))
