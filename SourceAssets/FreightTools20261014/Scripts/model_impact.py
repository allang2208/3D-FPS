"""Original brushless impact wrench with manufactured housing and exposed interfaces."""
import math
from mathutils import Matrix
import geometry as H

def build():
    # Battery casing has a separate bottom cup, split gasket, rails and release mechanisms.
    H.loft('Battery lower impact boot',[(0,8.0,9.9,1.05,0,1.0),(.35,8.6,10.3,1.15,0,1.0),(1.05,8.6,10.3,1.15,0,1.0)],'rubber',16)
    H.loft('Battery molded lower shell',[(1.0,8.5,10.2,1.1,0,1.0),(3.7,8.5,10.2,1.1,0,1.0),(4.1,8.1,9.7,1.0,0,1.0)],'plastic',16)
    H.frame('Battery shell separation gasket',(0,1.0,3.72),(8.51,10.21,.12),.12,'rubber',1.1)
    H.rounded('Battery top deck',(0,1.0,4.16),(7.60,8.7,.35),'teal',.9,.06)
    for side in (-1,1):
        H.rounded('Battery dovetail slide rail',(side*2.45,1.2,4.49),(.66,6.3,.44),'blacksteel',.22,.04)
        H.rounded('Battery release paddle',(side*4.16,-.6,2.87),(.30,3.5,1.48),'orange',.13,.06)
        for j in range(7):H.box('Battery release thumb rib',(side*4.34,-1.92+j*.43,2.88),(.12,.13,.99),'rubber',.035)
        for y in (-2.7,4.7):H.screw('Battery case screw',(side*3.1,y,4.10),.15)
    H.panel('Battery specification plate',(0,-4.115,2.30),6.4,2.10,'controls','-Y')
    for j in range(4):H.rounded('Battery charge indicator',(1.6+j*.40,5.14,2.55),(.23,.07,.24),'green' if j<3 else 'rubber',.05,.015)
    H.cylinder('Battery indicator button',(.65,5.15,2.55),.25,.07,'rubber','Y',48)
    H.panel('Battery safety serial label',(0,1.1,-.015),5.8,3.2,'serial','-Z')
    # Swept palm grip: continuously changing sections instead of intersecting straight cylinders.
    grip=H.loft('Ergonomic load bearing handle',[(4.5,4.65,4.70,.90,0,1.0),(5.0,4.50,4.52,.90,0,.8),
         (6.2,4.05,4.12,.95,0,.5),(8.5,3.85,3.85,.95,0,-.10),(10.6,4.05,4.10,1.0,0,-.6),
         (12.5,4.65,4.70,1.1,0,-.85),(13.5,5.45,5.35,1.3,0,-.72)],'teal',16)
    H.loft('Overmolded palm backstrap',[(5.2,3.40,1.00,.40,0,2.47),(6.4,3.40,.90,.40,0,2.15),
         (8.6,3.18,.87,.39,0,1.50),(10.5,3.35,.90,.40,0,1.03),(11.6,3.55,.88,.39,0,.96)],'rubber',14)
    for side in (-1,1):
        # Each cheek is a distinct injection overmold panel with rounded borders.
        H.loft('Soft touch handle cheek',[(5.5,.25,2.6,.12,side*2.00,.9),(6.8,.26,2.7,.12,side*1.94,.4),
              (9.0,.26,2.7,.12,side*1.85,-.2),(10.8,.25,2.6,.12,side*1.95,-.6)],'rubber',8)
        for j in range(11):
            z=5.9+j*.42;y=.75-(z-5.9)*.23
            H.cord('Handle chevron tread',[(side*2.01,y-.9,z),(side*2.03,y,z+.14),(side*2.01,y+.9,z)],.045,'plastic',5)
    # Motor housing is a carefully tapered rounded-rectangular solid along the tool axis.
    start=len(H.PARTS)
    motor=H.loft('Brushless motor clamshell', [(-5.7,5.5,5.8,2.10,0,0),(-5.1,6.7,6.7,2.35,0,0),
        (-3.7,7.75,7.10,2.55,0,0),(-1.0,8.0,7.35,2.60,0,0),(2.2,7.65,7.15,2.5,0,0),(3.4,6.9,6.8,2.35,0,0)],'teal',20)
    # Tangential vent cuts penetrate into a dark recessed plenum; the shell owns their thickness.
    for side in (-1,1):
        for j in range(5):
            H.cut(motor,(side*3.65,1.0,-3.6+j*.62),(1.65,.38,.30),.12)
            H.cut(motor,(side*3.65,-1.0,-3.6+j*.62),(1.65,.38,.30),.12)
        H.rounded('Vent internal dark plenum',(side*2.91,0,-2.45),(.17,3.0,3.1),'rubber',.08,.015)
    H.transform_since(start,Matrix.Translation((0,0,16.8))@Matrix.Rotation(math.pi/2,4,'X'))
    # A thin central mold seam continues over the back cap and top crown.
    H.cord('Housing centre parting seam',[(0,5.718,15.5),(0,5.718,19.718),(0,5.1,20.168),
        (0,3.7,20.368),(0,1.0,20.493),(0,-2.2,20.393),(0,-3.4,20.218)],.018,'rubber',1)
    for side in (-1,1):
        H.rounded('Motor badge mounting plinth',(side*3.87,-.30,16.75),(.23,4.0,2.16),'plastic',.10,.035)
        H.panel('Motor case identity badge',(side*3.995,-.30,16.75),3.8,2.0,'badge','X' if side>0 else '-X')
        for y,z in ((-2.3,18.4),(-2.0,14.8),(3.75,17.0)):
            H.screw('Motor housing assembly screw',(side*3.60,y,z),.19,'X')
    H.lathe('Rear elastomer bumper',(0,5.25,16.8),[(-.40,2.45),(-.30,2.77),(.10,2.90),(.35,2.68),(.40,2.40),(.40,.01),(-.40,.01)],'rubber','Y',96)
    for j in range(6):H.rounded('Rear exhaust grille slat',(-1.50+j*.60,5.69,16.75),(.19,.14,2.4),'blacksteel',.065,.03)
    # Cast alloy nose has a scalloped shoulder, circumferential groove and visible fasteners.
    H.lathe('Cast alloy impact gearbox',(0,-4.3,16.8),[(-1.0,3.06),(-.74,3.39),(.2,3.39),(1.35,2.98),
        (2.1,2.54),(2.55,2.45),(2.68,2.28),(2.68,.68),(-1.0,.68)],'satin','Y',112)
    H.ring('Gearbox shoulder seal',(0,-3.38,16.8),3.10,2.8,.19,'rubber','Y',96)
    H.ring('Gearbox retaining groove',(0,-6.41,16.8),2.49,2.40,.12,'blacksteel','Y',96)
    for j in range(4):
        a=math.pi*.25+j*math.pi/2;x=1.72*math.cos(a);z=16.8+1.72*math.sin(a)
        H.cylinder('Gearbox bolt counterbore',(x,-6.99,z),.32,.13,'blacksteel','Y',48)
        H.screw('Gearbox face fastener',(x,-7.06,z),.23,'Y')
    H.cylinder('Anvil bearing dust seal',(0,-7.03,16.8),.93,.35,'rubber','Y',72)
    H.box('Half inch square anvil',(0,-7.65,16.8),(1.27,1.25,1.27),'steel',.08)
    H.ring('Socket retaining collar',(0,-7.21,16.8),1.04,.82,.18,'blacksteel','Y')
    # Mounted deep impact socket keeps a true hexagonal mouth, interior and visible wall thickness.
    from model_toolkit import socket
    start=len(H.PARTS);socket('17 mm deep impact socket',(0,0,0),1.7/1.06,4.3,.635)
    for o in H.PARTS[start:]:o['surface_region']='blacksteel';H.uv(o,'blacksteel')
    H.transform_since(start,Matrix.Translation((0,-9.38,16.8))@Matrix.Rotation(math.pi/2,4,'X'))
    H.ring('Impact socket identification band',(0,-8.35,16.8),1.62,1.59,.21,'orange','Y')
    # Trigger, reversing slider and front work-light are individually mounted parts.
    trigger=H.loft('Variable speed trigger',[(10.4,2.10,1.12,.36,0,-2.72),(11.4,2.18,1.30,.37,0,-2.95),
        (12.7,2.20,1.12,.34,0,-2.92)],'rubber',12)
    for j in range(5):H.box('Trigger traction ridge',(0,-3.57,10.85+j*.31),(1.75,.08,.07),'plastic',.02)
    H.rounded('Forward reverse slide',(0,-1.35,13.3),(6.0,1.08,.70),'blacksteel',.30,.06)
    for side in (-1,1):H.box('Reverse thumb paddle',(side*3.0,-1.35,13.3),(.42,1.12,.82),'orange',.12)
    H.rounded('Work light bezel',(0,-2.72,5.28),(1.70,.65,.64),'rubber',.20,.05)
    H.rounded('Work light lens',(0,-3.05,5.30),(1.29,.07,.36),'white',.12,.015)
    # Folded stainless belt hook includes a spring return and fastening washer.
    H.cord('Belt hook stainless formed strap',[(2.9,1.5,5.25),(4.5,1.5,5.2),(4.8,1.5,4.2),(4.8,1.5,1.1),(4.2,1.5,.75),(3.9,1.5,1.35)],.16,'satin')
    H.rounded('Belt hook mount',(2.75,1.5,5.10),(.48,1.8,1.1),'steel',.20,.035)
    H.screw('Belt hook attachment screw',(3.02,1.5,5.10),.23,'X')
    H.COLLISIONS.extend([((0,1.0,2.4),(8.6,10.3,4.8)),((0,.15,8.8),(4.8,5.4,9.0)),
                         ((0,-.05,16.8),(8.0,11.6,7.4)),((0,-8.25,16.8),(3.4,6.7,3.4))])
