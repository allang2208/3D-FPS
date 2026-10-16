"""Build the approved potion-workbench concept as editable, textured geometry.

Only this ModelV1 directory is written. No render, UE process, runtime edits,
test runner or asset-library modification is performed.
"""
import bpy, math, json, random, sys, time
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
import geometry as g
from geometry import box,rounded,loft,lathe,cylinder,ring,torus,rod,tube,screw,text,mesh
ROOT=g.ROOT
RNG=random.Random(151026)
START=time.time()

def progress(s):print("POTION_AUTHORING: "+s,flush=True)
def X(name,p,size,key="green",r=.15):return box(name,p,size,key,r)
def rotate_parts(parts,pivot,axis,angle):
    mat=Matrix.Translation(Vector(pivot))@Matrix.Rotation(math.radians(angle),4,Vector(axis))@Matrix.Translation(-Vector(pivot))
    for o in parts:o.matrix_world=mat@o.matrix_world

def plank(name,p,size,grain="X"):
    ob=X(name,p,size,"wood",.23)
    ob.data.materials.append(g.MATS["endgrain"])
    ax=0 if grain=="X" else 1
    for f in ob.data.polygons:
        if abs(f.normal[ax])>.9:f.material_index=1
    if grain=="Y":
        for d in ob.data.uv_layers.active.data:d.uv=(d.uv.y,d.uv.x)
    return ob

def handle(name,a,b,key="brass"):
    a=Vector(a);b=Vector(b)
    # Handle lies on a vertical +Y facing drawer.
    rod(name+" left standoff",a,a+Vector((0,2.1,0)),.38,key)
    rod(name+" right standoff",b,b+Vector((0,2.1,0)),.38,key)
    rod(name+" grip",a+Vector((0,2.1,0)),b+Vector((0,2.1,0)),.46,key)
    for p in (a,b):cylinder(name+" escutcheon",p,.95,.2,key,(0,1,0),32)

def tray(name,p,w,h,key="steel"):
    x,y,z=p
    rounded(name+" bottom",(x,y,z+.18),(w,h,.36),key,1,.08)
    for dx in (-w/2+.2,w/2-.2):X(name+" rim",(x+dx,y,z+1),( .35,h,1.8),key,.12)
    for dy in (-h/2+.2,h/2-.2):X(name+" rim",(x,y+dy,z+1),(w,.35,1.8),key,.12)

def bottle(name,p,r=3,h=17,key="amberglass",liquid="clearliquid",label=0,stopper="cork",fill=.66,angle=math.pi/2):
    x,y,z=p
    neck=r*.42
    # Closed thin-wall volume with a real mouth, interior and thick bottom.
    outer=[(0,0),(0,r*.76),(.35,r*.94),(.8,r),(h*.59,r),(h*.72,r*.91),(h*.80,neck*1.07),
           (h*.91,neck),(h*.92,neck*1.12),(h*.97,neck*1.12),(h,neck),(h,neck-.10),
           (h*.91,neck-.10),(h*.80,neck-.10),(h*.71,r*.91-.14),(h*.59,r-.14),(.65,r-.16),(.5,0)]
    ob=lathe(name+" glass",p,outer,key,64)
    surface=min(fill*h,h*.66);rr=r-.22
    lathe(name+" liquid",p,[(.55,0),(.55,rr*.84),(.9,rr),(surface-.18,rr),(surface,rr-.08),(surface-.035,0)],liquid,56)
    if stopper=="cork":
        lathe(name+" cork",(x,y,z+h-.45),[(0,0),(0,neck*.81),(1.7,neck*.94),(2.15,neck*.87),(2.15,0)],"cork",40)
    elif stopper:
        cylinder(name+" screw cap",(x,y,z+h+.35),neck*1.23,1.4,stopper,sides=48)
        for j in range(24):
            a=j*math.tau/24
            rod(name+" cap knurl",(x+neck*1.23*math.cos(a),y+neck*1.23*math.sin(a),z+h-.05),
                (x+neck*1.23*math.cos(a),y+neck*1.23*math.sin(a),z+h+.8),.045,"brass",8)
    if label is not None:
        g.label_bottle(name+" label",(x,y),r+.025,z+h*.40,h*.28,label,angle=angle,span=1.45)
    return ob

def jar(name,p,r=4,h=11,label=6):
    x,y,z=p
    lathe(name+" glass",p,[(0,0),(0,r*.82),(.45,r),(h-.8,r),(h,r*.93),(h,r*.93-.16),
           (h-.9,r-.16),(.65,r-.16),(.55,0)],"glass",64)
    cylinder(name+" lid",(x,y,z+h+.3),r*1.04,1.2,"brass",sides=56)
    torus(name+" lid seam",(x,y,z+h-.25),r,.08,"rubber",steps=56)
    g.label_bottle(name+" label",(x,y),r+.028,z+h*.47,h*.43,label,span=1.55)

def leaf(name,p,length,width,rot=0):
    # Curved pointed lamina, center ridge and gently rolled edges.
    rows=7;vs=[];fs=[]
    for i in range(rows):
        t=i/(rows-1);ww=width*.5*math.sin(math.pi*t)
        for j in (-1,0,1):
            vs.append((j*max(.01,ww),length*t,math.sin(math.pi*t)*length*.055-abs(j)*width*.07))
    for i in range(rows-1):
        for j in range(2):
            a=i*3+j;fs.append((a,a+1,a+4,a+3))
    ob=mesh(name,vs,fs,"leaf",True)
    ob.matrix_world=g.FRAME@Matrix.Translation(Vector(p))@Matrix.Rotation(rot,4,"Z")@Matrix.Rotation(math.radians(18),4,"X")
    m=ob.modifiers.new("Leaf substance","SOLIDIFY");m.thickness=.035
    return ob

def herb_cluster(name,p,count=9,spread=3,height=12):
    x,y,z=p
    for i in range(count):
        a=RNG.uniform(0,math.tau);d=RNG.uniform(.2,spread)
        top=(x+d*math.cos(a),y+d*math.sin(a),z+height*RNG.uniform(.65,1))
        tube(name+" stem",[(x,y,z),(x+d*.4*math.cos(a),y+d*.4*math.sin(a),z+height*.45),top],.055,"leaf")
        for j in range(3):
            t=.40+j*.21
            q=(x+d*math.cos(a)*t,y+d*math.sin(a)*t,z+(top[2]-z)*t)
            leaf(name+" leaf",q,RNG.uniform(2.2,3.8),RNG.uniform(.7,1.4),a+j*2.4)

def bench():
    g.group("BenchBody");progress("tabletop, steel frame, drawers and storage")
    for i in range(5):
        plank(f"Main oak plank {i+1}",(130,7+i*14,91.5),(260,13.88,5))
    for i in range(5):
        ob=plank(f"Return oak plank {i+1}",(197+i*14,165,91.5),(13.88,190,5),"Y")
        # A real aperture passes through every intersecting plank.
        if abs(197+i*14-225)<37:g.cut_cylinder(ob,(225,106,92),29.6,18)
    for p,s in (
        ((130,4,86),(252,4,6)),((130,66,86),(252,4,6)),
        ((4,35,86),(4,66,6)),((256,130,86),(4,252,6)),
        ((194,165,86),(4,190,6)),((225,256,86),(66,4,6)),
        ((225,70,86),(66,4,6))):
        X("Structural upper rail",p,s,"green",.18)
    legpoints=[(4,4),(4,66),(50,4),(50,66),(194,4),(256,4),(194,70),(194,142),(256,142),(194,256),(256,256)]
    for i,(x,y) in enumerate(legpoints):
        X(f"Square steel leg {i}",(x,y,46),(4,4,84),"green",.18)
        X(f"Foot plate {i}",(x,y,4),(6,6,.65),"iron",.2)
        cylinder(f"Leveling thread {i}",(x,y,2.9),1.15,2.1,"steel",sides=24)
        cylinder(f"Leveling rubber foot {i}",(x,y,.8),2.3,1.6,"rubber",sides=32)
        for z in (12,81):
            screw("Rail fastening",(x,y+2.12,z),.38)
    # Left pedestal with actual door gaps and two drawers.
    for p,s in (((4.7,35,49),(1.1,60,70)),((49.2,35,49),(1.1,60,70)),((27,5,49),(45,1.2,70))):
        X("Left cabinet skin",p,s,"green",.2)
    plank("Left low shelf",(27,35,17),(43,59,2))
    for z in (76,57):
        X("Drawer dark reveal",(27,63.1,z),(43,2,18.3),"rubber",.16)
        X("Drawer folded front",(27,64.2,z),(42,1.4,17.3),"green",.35)
        X("Drawer bottom",(27,34,z-8),(40,55,.6),"green",.08)
        handle("Brass drawer pull",(18,65.05,z+1),(36,65.05,z+1))
        for xx in (7.5,46.5):
            for zz in (z-6.4,z+6.4):screw("Drawer corner rivet",(xx,65,zz),.19)
    # End pedestal and two shelves along the return.
    for p,s in (((256,221,49),(1.2,65,70)),((225,255,49),(59,1.2,70)),((225,187,49),(59,1.2,70))):
        X("Return cabinet skin",p,s,"green",.2)
    for z in (17,44):
        plank("Return storage shelf",(225,221,z),(59,65,2),"Y")
    for z in (76,56):
        X("Return drawer reveal",(195,221,z),(1.4,57,18.5),"rubber",.15)
        X("Return drawer front",(194.1,221,z),(1.4,56,17.6),"green",.3)
        for yy in (212,230):
            rod("Return pull standoff",(193.25,yy,z),(191.3,yy,z),.36,"brass")
            cylinder("Return pull escutcheon",(193.2,yy,z),.85,.18,"brass",(-1,0,0),24)
        rod("Return drawer handle",(191.3,212,z),(191.3,230,z),.44,"brass")
    # Main clear preparation inset and perimeter inlay.
    rounded("Prep ceramic panel",(119,43.5,94.22),(117,44,.42),"ceramic",.7,.06)
    for x in (60.7,177.3):X("Preparation edge inlay",(x,43.5,94.46),(.08,42,.035),"bronze",0)
    for y in (22,65):X("Preparation edge inlay",(119,y,94.46),(116,.08,.035),"bronze",0)
    for i in range(21):
        X("Preparation measurement tick",(67+i*5,63.7,94.49),(.055,.7 if i%5 else 1.2,.025),"brass",0)
    # Flush screws fixing the boards to rails, outside working area.
    for x in (9,51,185,250):
        for y in (7,62):screw("Countertop fixing",(x,y,94.02),.29,(0,0,1),"bronze")
    for y in (76,145,250):
        for x in (198,252):screw("Return countertop fixing",(x,y,94.02),.29,(0,0,1),"bronze")
    # Rear conduit, tie clips and protected power outlet.
    X("Rear power rail",(130,1.1,88),(246,2,3.2),"green",.15)
    X("Return power rail",(258.9,164,88),(2,186,3.2),"green",.15)
    X("Power junction",(250,65,86),(9,8,4),"green",.35)
    for x in (35,85,135,185,235):
        X("Cable retaining clip",(x,2.8,88),(1.1,.5,4),"steel",.12)
    # Low cabinet box and a reserve reagent tin.
    rounded("Low reagent case",(27,36,25),(27,28,14),"green",1,.15)
    X("Case lid seam",(27,36,30.8),(27.3,28.3,.22),"rubber",.05)
    for x in (15,39):
        for y in (23,49):X("Case corner fitting",(x,y,25),(1.5,1.5,13),"brass",.2)
    X("Case front latch",(27,50.4,29),(3,.5,5),"brass",.2)
    for x in (20,34):screw("Case latch screw",(x,50.4,26),.25)
    g.label_flat("Case inventory plate",(27,50.41,24),10,6,8)
    cylinder("Reserve brass tin",(229,234,25),7,14,"bronze",sides=56)
    torus("Tin rolled bottom",(229,234,18.2),7,.25,"brass")
    cylinder("Reserve tin lid",(229,234,32.3),7.3,1,"brass",sides=56)

def cauldron():
    g.group("CauldronBody");progress("thick-wall cauldron, thermal collar and furnace cabinet")
    profile=[(78,0),(78,10),(79,13),(82,16.8),(87,20.3),(92,23.4),(98,26),
             (104,27),(110,26.2),(116,24),(121,22.5),(124,22.3),
             (125,23.3),(126,23.7),(126.5,23.2),(126.5,21.8),(125.6,21.3),
             (124,21.4),(121,21.5),(116,23),(110,25.1),(104,25.9),
             (98,24.8),(92,22.2),(87,19),(82.3,15.5),(80,11),(80,0)]
    lathe("Cast iron cauldron with continuous inner wall",(225,106,0),profile,"iron",128)
    torus("Cauldron thick rolled lip",(225,106,125.5),22.8,.7,"steel",steps=128,tube=12)
    for a in (-math.pi/2,math.pi/2):
        x=225+25.2*math.cos(a);y=106+25.2*math.sin(a)
        axis=(math.cos(a),math.sin(a),0)
        cylinder("Handle welded socket",(x,y,116),2,1.4,"iron",axis,40)
        torus("Cast ring handle",(x+math.cos(a)*1.2,y+math.sin(a)*1.2,111),4.6,.73,"iron",axis,64,12)
        cylinder("Handle pivot pin",(x+math.cos(a)*1.3,y+math.sin(a)*1.3,116),.75,2.1,"steel",axis,28)
    ring("Stone thermal collar",(225,106,94.2),32.3,28.8,3.3,"stone",sides=128)
    ring("Collar outer fastening ring",(225,106,95.95),32.5,31.1,.32,"bronze",sides=128)
    for i in range(12):
        a=i*math.tau/12
        screw("Collar inset fastener",(225+31.8*math.cos(a),106+31.8*math.sin(a),96.14),.28,(0,0,1),"brass")
    for a in (0,math.pi/2,math.pi,3*math.pi/2):
        rod("Cauldron cradle upright",(225+19*math.cos(a),106+19*math.sin(a),68),
            (225+25*math.cos(a),106+25*math.sin(a),97),1.1,"iron")
    ring("Lower structural cradle",(225,106,72),21,18.7,2,"iron")
    # Temperature probe with its own mechanical clamp.
    X("Probe clamp",(244,106,125),(5,3,1.3),"steel",.2)
    rod("Probe insertion stem",(243,106,126),(243,106,116),.32,"steel")
    rounded("Temperature probe enclosure",(245,106,131),(3,3,9),"ivory",.5,.08)
    X("Probe status face",(243.44,106,131),(.12,2.1,5.1),"display",.1)
    text("Temperature readout","72",(243.36,106,132),.85,"displaytext",(-1,0,0),.006)
    tube("Probe signal cable",[(246.6,106,129),(252,106,128),(256,112,116),(258,127,99),(259,141,89)],.18,"rubber")
    # Under-counter heater chamber: thermal enclosure and actual front panel gaps.
    for p,s in (((254.2,106,56),(1.3,56,68)),((225,78,56),(57,1.3,68)),((225,134,56),(57,1.3,68))):
        X("Heat chamber wall",p,s,"iron",.25)
    X("Heat chamber front",(195.8,106,56),(1.2,55,68),"iron",.3)
    X("Heater service door reveal",(195.0,106,55),(.7,47,54),"rubber",.4)
    X("Heater service door",(194.5,106,55),(.8,45.5,52.5),"iron",.55)
    for yy in (85,127):
        for zz in (32,78):screw("Heater door rivet",(193.99,yy,zz),.33,(-1,0,0),"bronze")
    for zz in (38,71):
        cylinder("Service door hinge",(194,128,zz),.8,6,"bronze",(0,0,1),32)
    rod("Service door pull",(193.3,86,51),(191.3,86,51),.42,"brass")
    rod("Service door pull",(193.3,86,62),(191.3,86,62),.42,"brass")
    rod("Service door pull grip",(191.3,86,51),(191.3,86,62),.5,"brass")
    # Thin brass circular alchemical emblem on the door.
    torus("Door arcane seal",(193.98,108,60),7,.085,"brass",(-1,0,0),72,6)
    tube("Door seal triangle",[(193.95,108,67),(193.95,101.8,56.5),(193.95,114.2,56.5),(193.95,108,67)],.09,"brass",False)
    rod("Door seal bar",(193.95,101.7,60),(193.95,114.3,60),.07,"brass")
    X("Isolation strip",(225,142,94.45),(69,5,.9),"stone",.3)

    g.group("HeaterRing")
    ring("Rune heater bronze band",(225,106,102.5),28.2,27.1,7.5,"brass",sides=128)
    for z in (98.8,106.2):torus("Heater rolled border",(225,106,z),28.22,.34,"bronze",steps=128)
    patterns=[
        [[(-.8,-1.4),(0,1.4),(.8,-1.4),(-.8,-1.4)]],
        [[(-.8,-1.4),(.8,1.4)],[(-.8,1.4),(.8,-1.4)]],
        [[(0,-1.4),(0,1.4)],[(-.8,.2),(0,.9),(.8,.2)]],
        [[(-.8,-1.4),(.7,-.5),(-.7,.5),(.8,1.4)]],
        [[(-.8,0),(0,1.4),(.8,0),(0,-1.4),(-.8,0)]],
        [[(-.8,1.4),(-.8,-1.4),(.8,-1.4),(.8,.2),(-.8,.2)]],
    ]
    for i in range(24):
        a=i*math.tau/24
        tangent=Vector((-math.sin(a),math.cos(a),0))
        center=Vector((225+28.26*math.cos(a),106+28.26*math.sin(a),102.5))
        for j,stroke in enumerate(patterns[i%len(patterns)]):
            pts=[tuple(center+tangent*u+Vector((0,0,v))) for u,v in stroke]
            tube(f"Inlaid rune {i+1} stroke {j}",pts,.065,"rune",False)
        if i%3==0:
            screw("Heater band anchor",(225+28.27*math.cos(a),106+28.27*math.sin(a),105.3),.2,(math.cos(a),math.sin(a),0),"bronze")
    # Eight dark vent slots beneath the rune band reveal a restrained amber core.
    ring("Heater inner light chamber",(225,106,97.4),27.3,25.8,1,"rune",sides=96)
    for i in range(16):
        a=i*math.tau/16
        rod("Heater vent division",(225+27.2*math.cos(a),106+27.2*math.sin(a),96),
            (225+27.7*math.cos(a),106+27.7*math.sin(a),98.8),.4,"iron")

    g.group("PotionSurface")
    lathe("Teal potion meniscus",(225,106,0),[(116.8,0),(116.8,22.2),(119.15,22.0),(119.4,21.9),(119.25,21.6),(119.2,0)],"potion",128)
    for r in (4.2,8.7,14.0):
        torus("Subtle liquid ripple",(225,106,119.24),r,.045,"potion",steps=96,tube=6)
    for i in range(7):
        a=RNG.uniform(0,math.tau);r=RNG.uniform(3,18);rr=RNG.uniform(.25,.65)
        lathe("Small surface bubble",(225+r*math.cos(a),106+r*math.sin(a),119.2),
            [(0,rr),(.18,rr*.8),(.32,0)],"potion",24,False)

def centrifuge():
    progress("centrifuge enclosure, chamber, eight sample slots, controls and hinged lid")
    origin=(225,222,94);angle=-90
    g.group("CentrifugeBody",origin,angle)
    for x in (-19,19):
        for y in (-18,18):
            cylinder("Anti vibration foot",(x,y,1),2.4,2,"rubber",sides=32)
            cylinder("Foot threaded stem",(x,y,2.2),.8,1,"steel",sides=24)
    loft("Deep green centrifuge chassis",[(2,48,49,5,0,0),(3,52,54,5,0,0),(8,52,54,5,0,0),(9,50,52,5,0,0)],"green")
    shell=loft("Cream formed centrifuge housing",[(8,50,52,5,0,0),(10,52,54,6,0,0),(23,52,54,6,0,0),(28,50,52,7,0,0),(31,46,47,8,0,0)],"ivory")
    g.cut_cylinder(shell,(0,1,29),19.6,31)
    g.bevel(shell,.16,3)
    # Stainless bowl with a closed rounded bottom.
    lathe("Recessed stainless rotor chamber",(0,1,0),[(13.5,0),(13.5,12),(15,17),(18,19.45),(30.7,19.45),
          (31.1,19.7),(31.4,19.4),(30.8,19.1),(18.4,19.1),(15.3,16.8),(14,11.8),(14,0)],"steel",112)
    torus("Bowl rim gasket",(0,1,31.0),19.8,.32,"rubber",steps=112)
    ring("Bowl polished rim",(0,1,31.26),20.4,19.6,.24,"steel",sides=112)
    # Sloped operator fascia physically protrudes from the shell.
    fascia=rounded("Operator fascia",(0,-26.6,17),(36,12,.7),"green",2,.1)
    fascia.matrix_world=g.FRAME@Matrix.Translation(Vector((0,-26.6,17)))@Matrix.Rotation(math.radians(90),4,"X")
    screen=X("Display recessed bezel",(-3,-27.1,18.7),(15,.45,6.8),"rubber",.55)
    X("Digital screen glass",(-3,-27.37,18.7),(13.5,.13,5.4),"display",.3)
    text("Centrifuge screen READY","READY",(-3,-27.45,19.35),1.75,"displaytext",(0,-1,0),.006)
    text("Centrifuge balanced display","BALANCED  /  08",(-3,-27.45,17.25),.68,"displaytext",(0,-1,0),.004)
    for x,key in ((-12,"ivory"),(-6,"green"),(0,"ivory")):
        cylinder("Pushbutton metal rim",(x,-27.15,12.8),1.05,.4,"steel",(0,-1,0),32)
        cylinder("Pushbutton cap",(x,-27.43,12.8),.76,.38,key,(0,-1,0),32)
    cylinder("Control knob skirt",(11,-27.1,15),2.6,.55,"steel",(0,-1,0),48)
    cylinder("Control knob rubber grip",(11,-27.7,15),2.05,1.2,"rubber",(0,-1,0),48)
    for j in range(24):
        a=j*math.tau/24
        rod("Control knob knurl",(11+2.06*math.cos(a),-27.3,15+2.06*math.sin(a)),
            (11+2.06*math.cos(a),-28.1,15+2.06*math.sin(a)),.07,"rubber",8)
    X("Knob white index",(11,-28.34,16.25),(.15,.04,1),"white",.025)
    for x in (-16,16):
        for z in (12.5,21.5):screw("Fascia screw",(x,-27.13,z),.23,(0,-1,0))
    text("Centrifuge fascia name","ARCANE LAB / C-08",(0,-27.14,24),.66,"bronze",(0,-1,0),.004)
    # Side cooling louvers are separate real slats over a recessed grille.
    X("Vent dark cavity",(25.68,5,15),(.12,18,10),"rubber",.35)
    for j in range(8):
        ob=X("Vent pressed louver",(25.88,5,11+j*1.12),(.4,17.4,.35),"green",.1)
        ob.matrix_world=ob.matrix_world@Matrix.Rotation(math.radians(-20),4,"Y")
    for yy in (-6,16):screw("Service side screw",(25.82,yy,20.7),.24,(1,0,0))
    # Rear power port and routed strain relief.
    X("Power connector surround",(9,26.4,8),(5,.5,3.3),"rubber",.2)
    cylinder("Cable strain relief",(9,27.4,8),.8,2,"rubber",(0,1,0),24)
    tube("Centrifuge power cable",[(9,28.4,8),(10,31,6),(18,33,3),(25,33,-5),(34,31,-6)],.24,"rubber")
    for x in (-16,16):
        cylinder("Rear hinge knuckle",(x,23.5,31.4),1.2,6,"steel",(1,0,0),40)
        cylinder("Hinge pin",(x,23.5,31.4),.46,7,"brass",(1,0,0),24)
    X("Front lid latch socket",(0,-22,30),(5,2,2),"rubber",.35)

    g.group("CentrifugeRotor",origin,angle)
    rotor_start=len(g.PARTS)
    lathe("Precision rotor conical hub",(0,1,0),[(14.1,0),(14.1,4),(15.5,5.5),(20,16.5),(23,16.9),(24,15.8),(24,4),(26.1,3.6),(26.1,0)],"steel",96)
    # Eight evenly spaced tube seats: real holes cut through the rotor.
    rotor=g.PARTS[-1]
    for i in range(8):
        a=i*math.tau/8;x=12.1*math.cos(a);y=1+12.1*math.sin(a)
        g.cut_cylinder(rotor,(x,y,23),2.25,14)
        ring("Tube retaining collar",(x,y,24.1),2.45,1.88,.8,"rubber",sides=40)
        bottle(f"Balanced sample {i+1}",(x,y,17),1.66,10.3,"glass","greenliquid" if i%2==0 else "clearliquid",None,"green",.73)
        text("Rotor sample index",str(i+1),(14.95*math.cos(a),1+14.95*math.sin(a),24.1),.75,"bronze",(0,0,1),.008)
    cylinder("Rotor hub bolt",(0,1,27),2.35,2,"steel",sides=6)
    ring("Hub brass index",(0,1,27.9),2.55,2.3,.18,"brass",sides=48)
    pivot=tuple(g.FRAME@Vector((0,1,14)))
    rotorroot=g.parent_keep(g.PARTS[rotor_start:],"Pivot_CentrifugeRotor",pivot)
    rotorroot["axis"]="World +Z";rotorroot["authoring_state"]="stationary"

    g.group("CentrifugeLid",origin,angle)
    lid_start=len(g.PARTS)
    rounded("Centrifuge lid outer shell",(0,.5,33.4),(46,46,3.6),"ivory",8,.2)
    rounded("Lid underplate",(0,.5,31.7),(42.8,42.8,.8),"steel",7,.1)
    # Closed-position circular gasket and central pressure relief plate.
    torus("Lid seal",(0,1,31.1),19.5,.48,"rubber",steps=96)
    cylinder("Lid inner pressure disc",(0,1,31.35),17.9,.45,"ivory",sides=96)
    cylinder("Lid central inset",(0,1,31.02),2.5,.28,"rubber",sides=48)
    cylinder("Lid central screw",(0,1,30.84),.63,.16,"steel",sides=6)
    for x in (-14,14):
        for y in (-14,14):screw("Lid underside screw",(x,y,31.14),.28,(0,0,-1))
    X("Lid handle",(0,-20.5,35.9),(15,2.2,2.2),"green",.7)
    X("Lid catch tongue",(0,-21.1,30.5),(3,1,2),"steel",.25)
    hinge=Vector((0,23.5,31.4))
    worldhinge=g.FRAME@hinge
    axis=g.FRAME.to_3x3()@Vector((1,0,0))
    rotate_parts(g.PARTS[lid_start:],worldhinge,axis,-103)
    root=g.parent_keep(g.PARTS[lid_start:],"Pivot_CentrifugeLid",tuple(worldhinge))
    root["hinge_axis_world"]=list(axis);root["open_angle_degrees"]=-103
    root["authoring_state"]="open at rest; rotate +103 degrees around hinge axis to close"

def dispensing():
    g.group("DispensingSet",(225,168,94),-90)
    progress("graduated dispensing glass, valves, vial rack and specimen tray")
    tray("Dispensing tray",(0,-2,0),43,25,"steel")
    X("Dispensing anti slip insert",(0,-2,.48),(41,23,.15),"rubber",.5)
    # Raised glass cylinder and metal cradle at the back of the tray.
    cylinder("Dispenser base",(8,5,1.1),7.5,1.3,"brass",sides=64)
    for x in (3,13):
        rod("Dispenser stand upright",(x,5,1.6),(x,5,22),.45,"steel")
    ring("Dispenser retaining ring",(8,5,18),5.8,5.3,.7,"brass",sides=64)
    lathe("Graduated dispensing vessel",(8,5,12),[(0,0),(0,3),(1.6,5),(14.9,5),(15.8,5.3),(16.1,5.3),
          (16.1,4.9),(15,4.7),(1.8,4.7),(.4,2.8),(.4,0)],"glass",80)
    lathe("Dispenser amber liquid",(8,5,12.45),[(0,0),(0,2.7),(1.5,4.5),(8.2,4.5),(8.25,0)],"clearliquid",72)
    # Graded scale is actual printing/geometry on the operator-facing glass surface.
    for i in range(1,11):
        z=15+i
        rod("Graduation mark",(7.8,0.1,z),(9.2 if i%5==0 else 8.65,0.1,z),.035,"paper",8)
        if i%5==0:text("Graduation number",str(i*25),(10.1,.24,z),.7,"paper",(0,-1,0),.004)
    rod("Bottom outlet",(8,5,12),(8,5,9.4),.5,"steel")
    rod("Valve to filling nozzle",(8,5,9.6),(8,-1,9.6),.55,"brass")
    rod("Filling nozzle",(8,-1,9.6),(8,-1,7.3),.4,"steel")
    cylinder("Valve spindle",(9.1,3,10.1),.4,2,"steel",(1,0,0),24)
    rod("Valve lever",(10.1,3,10.1),(10.1,3,14),.28,"green")
    # Six narrow receiving vials with actual mouths and visible liquid levels.
    for i in range(6):
        x=-15+(i%3)*5.7;y=-8+(i//3)*6.5
        bottle(f"Receiving vial {i+1}",(x,y,1),1.7,8.5,"glass","clearliquid",None,"cork",.34)
    for xx in (-18.7,2.3):X("Vial rack side",(xx,-4.75,3.4),(.6,15,5),"brass",.1)
    for zz in (2,5):
        plate=X("Vial rack bored plate",(-8.2,-4.75,zz),(21,15,.4),"brass",.1)
        for i in range(6):g.cut_cylinder(plate,(-15+(i%3)*5.7,-8+(i//3)*6.5,zz),1.95,2)
    lathe("Stainless sample cup",(16,-7,1),[(0,0),(0,2.7),(6,3.2),(6.2,3.1),(6.2,2.9),(.3,2.4),(.3,0)],"steel",56)

def balance_and_finished():
    g.group("WeighingSet");progress("brass balance, utensils and finished potion bottles")
    tray("Weighing tray",(48,45,94),23,26,"steel")
    rounded("Balance marble base",(48,36.5,95.6),(14,8,1.1),"stone",1,.15)
    cylinder("Balance foot",(48,36.5,97),2.8,2,"brass",sides=48)
    rod("Balance central pillar",(48,36.5,97),(48,36.5,115),.43,"brass")
    torus("Balance fulcrum ring",(48,36.5,115),1.2,.22,"brass",(0,1,0),40,8)
    rod("Balance beam",(38.5,36.5,115),(57.5,36.5,115),.23,"brass")
    rod("Balance pointer",(48,36.6,115),(48,36.6,110),.09,"brass",12)
    for x in (39,57):
        lathe("Balance suspended pan",(x,36.5,103.4),[(0,0),(.5,3.3),(1,3.8),(1.15,3.8),(.65,3.2),(.2,0)],"brass",64)
        for a in (0,math.tau/3,2*math.tau/3):
            # Fine linked chain made from small actual ovals along the suspension line.
            aa=Vector((x+3.4*math.cos(a),36.5+3.4*math.sin(a),104.4));bb=Vector((x,36.5,114.8))
            delta=bb-aa;count=17
            for i in range(count):
                p=aa+delta*(i+.5)/count
                axis=(1,0,0) if i%2 else (0,1,0)
                torus("Balance chain link",p,.17,.045,"brass",axis,12,5)
    lathe("Weighing mortar",(45,50,95),[(0,0),(0,2.9),(1,4.2),(4.4,5),(4.7,4.8),(4.7,4.4),(1.6,3.4),(.7,0)],"steel",72)
    rod("Pestle",(43.5,49,97),(50,47,103),.55,"brass",32)
    lathe("Powder dish",(54,53,95),[(0,0),(.25,3),(.8,3.5),(1,3.4),(.5,2.8),(.2,0)],"steel",48)
    rod("Micro spatula handle",(55,51.5,96),(58,45.5,96.3),.17,"steel")
    X("Spatula blade",(55,51.8,96),(1.5,2,.14),"steel",.1)
    for i in range(4):
        cylinder("Calibration weight",(42+i*2,57,96.2),.65,1.4,"brass",sides=24)
        cylinder("Weight knob",(42+i*2,57,97.05),.26,.35,"brass",sides=16)
    g.group("FinishedPotionTray")
    tray("Finished potion tray",(20,46,94),27,18,"brass")
    X("Finished tray felt",(20,46,94.5),(25.5,16.5,.25),"rubber",.4)
    for i,(xx,key,hh) in enumerate(((11.5,"redliquid",18),(20,"greenliquid",21),(28.5,"blueliquid",24))):
        bottle("Finished "+key,(xx,46,94.7),3.3,hh,"glass",key,None,"steel",.64)
        # Fine wire neck band makes the three signature potions a consistent family.
        torus("Bottle neck binding",(xx,46,94.7+hh*.82),1.54,.13,"brass",steps=48)
        g.label_bottle("Potion seal",(xx,46),3.34,94.7+hh*.43,4,i,span=1)

def books_and_reagents():
    g.group("ReagentRack");progress("two-tier shelf, leather books, labelled reagents and herbs")
    # Rear shelf is low and open, with slender uprights and bottle retaining rails.
    for x in (68,111,166,187):
        X("Reagent rack upright",(x,9,108),(1.2,1.6,28),"green",.15)
        X("Rack foot",(x,9,94.7),(4,6,1.4),"green",.2)
        screw("Rack mounting screw",(x,7.2,95.4),.22,(0,0,1),"brass")
    for z in (98,118):
        plank("Reagent shelf",(128,11.5,z),(124,15,1.8))
        rod("Shelf front retaining rail",(66.5,19.3,z+3.5),(189.5,19.3,z+3.5),.22,"steel")
        for xx in (66.5,189.5):
            rod("Rack rail stand",(xx,19.3,z+1),(xx,19.3,z+3.5),.2,"steel")
    # Books stay on the tabletop beside the reagent rack.
    for i,(w,h,key) in enumerate(((3.5,23,"bookgreen"),(4.2,26,"leather"),(3.1,21,"oxblood"),(5,25,"bookgreen"),(5.2,22,"leather"))):
        x=41+i*4.9;y=12;z=94
        X("Bound book page block",(x,y,z+h/2),(w-.38,15,h-.65),"pages",.18)
        for dx in (-w/2,w/2):X("Leather book board",(x+dx,y,z+h/2),(.35,16,h),key,.13)
        X("Rounded leather spine",(x,y+7.6,z+h/2),(w+.3,.9,h),key,.35)
        for zz in (z+2,z+5,z+h-5,z+h-2):
            X("Raised spine band",(x,y+8.1,zz),(w+.3,.25,.35),"brass",.06)
        text("Book spine title","A R C A N A",(x,y+8.25,z+h*.54),.62,"brass",(0,1,0),.008)
        for zz in (z+.8,z+h-.8):
            X("Book spine end trim",(x,y+8.1,zz),(w,.08,.11),"brass",0)
    # Individually shaped vessels on both tiers, with empty spaces between groups.
    specs=[
        (71,11,99,2.7,14,"amberglass","redliquid",0),
        (80,11,99,2.9,16,"glass","clearliquid",2),
        (91,10,99,3.1,13,"amberglass","greenliquid",1),
        (117,11,99,2.8,15,"amberglass","clearliquid",7),
        (128,11,99,3.1,12,"glass","blueliquid",3),
        (141,11,99,2.6,16,"amberglass","greenliquid",4),
        (175,11,99,4.1,12,"glass","redliquid",5),
        (77,11,119,3.3,20,"amberglass","clearliquid",5),
        (89,11,119,3,16,"glass","redliquid",0),
        (104,11,119,2.7,13,"amberglass","greenliquid",1),
        (129,11,119,3.9,23,"amberglass","clearliquid",7),
        (162,11,119,3.2,19,"amberglass","clearliquid",13),
    ]
    for i,(x,y,z,r,h,glass,liq,lab) in enumerate(specs):
        bottle(f"Reagent bottle {i+1}",(x,y,z),r,h,glass,liq,lab,"cork",RNG.uniform(.4,.67))
    jar("Herb jar",(146,11,119),5.3,11.5,6)
    herb_cluster("Dry herb in jar",(146,11,120),5,2.8,8)
    jar("Crystal jar",(155,11,99),3.8,12,3)
    for i in range(11):
        a=RNG.uniform(0,math.tau);rr=RNG.uniform(.2,2.6)
        cylinder("Blue mineral shard",(155+rr*math.cos(a),11+rr*math.sin(a),100+RNG.uniform(1,6)),.55,RNG.uniform(2,4),"blueliquid",
                 (RNG.uniform(-.3,.3),RNG.uniform(-.3,.3),1),6,.02)
    lathe("Fresh herb ceramic bowl",(116,11,119),[(0,0),(0,3.5),(1,5.1),(6,7.3),(6.3,7.2),(6.3,6.7),(1.5,4.5),(.5,0)],"ceramic",72)
    herb_cluster("Fresh herb bunch",(116,11,122),12,4,12)
    # Stirring spoons and stirrers share one heavy brass cup at the far right.
    lathe("Brass utensil cup",(183,35,94),[(0,0),(0,4),(14,4.2),(14.3,4.1),(14.3,3.75),(.4,3.5),(.4,0)],"brass",64)
    for i in range(5):
        a=i*math.tau/5;bottom=Vector((183+1.5*math.cos(a),35+1.5*math.sin(a),94.6))
        top=Vector((183+4*math.cos(a),35+4*math.sin(a),120+i%2*3))
        rod("Long stirring utensil",bottom,top,.27,"wood" if i%2 else "steel",20)
        if i<3:
            ob=lathe("Spoon bowl",top,[(0,0),(.2,1.5),(2,1.8),(2.2,1.7),(.5,1.3),(.15,0)],"steel",40)
            ob.scale=(.65,1,1)
    # Small side folio on the left, outside the preparation rectangle.
    X("Closed recipe folio",(23,28,95.5),(21,13,2.5),"leather",.3)
    X("Folio page block",(23,28,95.55),(20.2,12.5,1.7),"pages",.1)
    for z in (94.25,96.75):X("Folio leather cover",(23,28,z),(21.3,13.5,.3),"leather",.15)
    torus("Folio gold seal",(23,28,96.94),3.1,.055,"brass",steps=64,tube=6)
    tube("Folio gold triangle",[(23,31,96.94),(20.4,26.5,96.94),(25.6,26.5,96.94),(23,31,96.94)],.06,"brass",False)

def lamp():
    g.group("TaskLamp");progress("articulated lamp, springs, reflector and continuous cabling")
    cylinder("Lamp weighted base",(15,10,95),7.4,2,"green",sides=80)
    cylinder("Lamp base trim",(15,10,94.2),7.45,.35,"rubber",sides=80)
    cylinder("Lamp swivel",(15,10,97.4),2.1,3,"brass",sides=48)
    a=Vector((15,10,100));b=Vector((13,10,133));c=Vector((42,29,153))
    for off in (-1.1,1.1):
        d=Vector((0,off,0))
        rod("Lower parallelogram lamp arm",a+d,b+d,.48,"green")
        rod("Upper parallelogram lamp arm",b+d,c+d,.48,"green")
    for p in (a,b,c):
        cylinder("Lamp pivot boss",p,1.5,4,"green",(0,1,0),40)
        screw("Lamp adjustment bolt",p+Vector((0,2.1,0)),.58,(0,1,0),"brass")
    # Tension springs: an actual continuous helical wire between arm anchors.
    for aa,bb in ((a+Vector((1,0,5)),b+Vector((1,0,-5))),(b+Vector((5,0,0)),c+Vector((-5,0,0)))):
        delta=bb-aa;zaxis=delta.normalized();u=zaxis.cross(Vector((0,1,0))).normalized();v=zaxis.cross(u)
        pts=[tuple(aa+delta*(j/180)+.48*(math.cos(j/180*math.tau*18)*u+math.sin(j/180*math.tau*18)*v)) for j in range(181)]
        tube("Lamp tension spring",pts,.075,"steel",False)
    rod("Lamp shade neck",c,(45,34,151),.8,"green",40)
    start=len(g.PARTS)
    profile=[(0,2.2),(-1.5,2.7),(-3,4.1),(-5.5,6.5),(-8,8.8),(-9,9.1),(-9.4,8.9),
             (-9.4,8.55),(-8,8.48),(-5.5,6.18),(-3,3.8),(-1.5,2.4),(0,1.9)]
    lathe("Spun green lamp shade",(45,36,151),profile,"green",96)
    lathe("Lamp pale reflector",(45,36,151),[(-1.5,2.35),(-3,3.73),(-5.5,6.11),(-8.4,8.55),(-8.6,8.45),(-5.5,6),(-3,3.63),(-1.5,2.2)],"ivory",96)
    cylinder("Warm lamp diffuser",(45,36,143),7.35,.18,"lamp",sides=80)
    torus("Lamp shade rolled edge",(45,36,141.6),8.75,.25,"steel",steps=96)
    rotate_parts(g.PARTS[start:],(45,36,151),(1,0,0),-18)
    cylinder("Lamp top vent cap",(45,36,151.3),1.9,1,"green",sides=40)
    tube("Lamp arm cable",[(15,10,97),(14,11,104),(12,11,132),(25,20,143),(42,30,152),(45,35,152)],.15,"rubber")
    tube("Lamp supply cable",[(15,8,95),(15,3,94.5),(12,1.5,94.3),(9,1.5,91),(9,2,88),(35,2,88)],.2,"rubber")
    cylinder("Lamp switch",(16.5,12.5,96.3),.8,.7,"rubber",sides=24)

def setup_view():
    # Saved authoring viewport only. No render engine invocation.
    bpy.context.scene.world.color=(.18,.18,.18)
    target=Vector((120,125,80));eye=Vector((-290,410,285))
    rotation=(target-eye).to_track_quat("-Z","Y")
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                space=area.spaces.active
                space.clip_end=10000;space.clip_start=.1
                space.region_3d.view_distance=460
                space.region_3d.view_location=target
                space.region_3d.view_rotation=rotation
                space.shading.type="MATERIAL"
    bpy.ops.object.select_all(action="DESELECT")

def author():
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system="METRIC";bpy.context.scene.unit_settings.scale_length=.01
    bpy.context.scene.unit_settings.length_unit="CENTIMETERS"
    g.setup_materials()
    bench();cauldron();centrifuge();dispensing();balance_and_finished();books_and_reagents();lamp()
    g.group("AssemblyAnchors")
    anchors={"MainPreparation":(119,43.5,94.5),"CauldronSteam":(225,106,126.6),"CentrifugeInteract":(194,222,111),
             "FillingNozzle":(224,160,101.3),"FinishedPotions":(20,46,95),"Operator":(112,115,0)}
    for name,p in anchors.items():
        o=bpy.data.objects.new("Anchor_"+name,None);g.COLLECTION.objects.link(o);o.location=p;o.empty_display_size=4
    setup_view()
    for im in bpy.data.images:
        if im.source=="FILE":im.pack()
    bpy.context.scene["asset_identity"]="PotionWorkbench_ConceptV1_Authored"
    bpy.context.scene["coordinate_units"]="cm, Z up; X right, Y toward operator from rear edge"
    bpy.context.scene["stage"]="Editable authored model; not UE imported or gameplay registered"
    bpy.context.scene["no_render_or_tests"]=True
    source=ROOT/"Authored/PotionWorkbench_Editable.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    progress("editable source saved; creating export components")
    export_components()

def export_components():
    scene=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get()
    original=list(scene.objects);groups={}
    for src in g.PARTS:
        ev=src.evaluated_get(deps)
        me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        me.transform(src.matrix_world)
        ob=bpy.data.objects.new("EXPORT_"+src.name,me);scene.collection.objects.link(ob)
        groups.setdefault(src["component"],[]).append(ob)
    # Export component origins preserve hinge/rotor pivots for future interaction.
    pivots={"CentrifugeLid":list(bpy.data.objects["Pivot_CentrifugeLid"].location),
            "CentrifugeRotor":list(bpy.data.objects["Pivot_CentrifugeRotor"].location),
            "PotionSurface":[225,106,119.2],"HeaterRing":[225,106,102.5]}
    export_objects=[];records=[]
    for name,objects in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objects:ob.select_set(True)
        bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
        ob=bpy.context.object;ob.name="SM_PW_"+name
        # Material indices are captured before clearing the slot table.
        slots=list(ob.data.materials);unique=[];mapping={}
        for i,mat in enumerate(slots):
            if mat not in unique:unique.append(mat)
            mapping[i]=unique.index(mat)
        indices=[mapping[f.material_index] for f in ob.data.polygons]
        ob.data.materials.clear()
        for mat in unique:ob.data.materials.append(mat)
        for face,index in zip(ob.data.polygons,indices):face.material_index=index
        pivot=Vector(pivots.get(name,(0,0,0)))
        ob.data.transform(Matrix.Translation(-pivot));ob.location=pivot
        # Triangulate only the export copy; source keeps editable construction.
        g.select(ob)
        tri=ob.modifiers.new("Explicit export triangulation","TRIANGULATE");tri.quad_method="FIXED";tri.ngon_method="BEAUTY"
        bpy.ops.object.modifier_apply(modifier=tri.name)
        ob.data.calc_loop_triangles()
        ob["assembly_component"]=name
        ob["pivot_cm"]=list(pivot)
        records.append({"name":ob.name,"source_component":name,"author_objects":len(objects),
                        "triangles":len(ob.data.loop_triangles),"vertices":len(ob.data.vertices),
                        "pivot_cm":list(pivot),"materials":[m.name for m in ob.data.materials]})
        export_objects.append(ob)
    for ob in original:
        bpy.data.objects.remove(ob,do_unlink=True)
    for im in bpy.data.images:
        if im.source=="FILE":im.filepath="//../Textures/"+Path(im.filepath).name
    # Save a second portable, consolidated, already triangulated authoring file.
    setup_view()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Export/PotionWorkbench_Assembly.blend"))
    for ob in export_objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=export_objects[0]
    progress("exporting material-embedded GLB and component FBX files")
    bpy.ops.export_scene.gltf(filepath=str(ROOT/"Export/PotionWorkbench_Assembly.glb"),
        export_format="GLB",use_selection=True,export_apply=False,export_animations=False,
        export_yup=True,export_materials="EXPORT")
    bpy.ops.export_scene.fbx(filepath=str(ROOT/"Export/PotionWorkbench_Assembly.fbx"),
        use_selection=True,object_types={"MESH"},apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_tspace=True,
        add_leaf_bones=False,bake_anim=False,path_mode="COPY",embed_textures=True)
    for ob,record in zip(export_objects,records):
        g.select(ob)
        loc=ob.location.copy();ob.location=(0,0,0)
        bpy.ops.export_scene.fbx(filepath=str(ROOT/"Export"/(ob.name+".fbx")),
            use_selection=True,object_types={"MESH"},apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
            axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_tspace=True,
            add_leaf_bones=False,bake_anim=False,path_mode="STRIP")
        ob.location=loc
        record["fbx"]=ob.name+".fbx"
    report={"stage":"authored_model_exported","asset":"PotionWorkbench",
            "source":"Authored/PotionWorkbench_Editable.blend","assembly":"Export/PotionWorkbench_Assembly.blend",
            "concept":"../Concept/potion-workbench-v1.png","units":"centimeters",
            "components":records,"triangles":sum(r["triangles"] for r in records),
            "source_mesh_objects":sum(r["author_objects"] for r in records),
            "seconds":round(time.time()-START,2),
            "texture_manifest":"texture_manifest.json",
            "open_lid":{"hinge_pivot_cm":pivots["CentrifugeLid"],"axis_world":[0,-1,0],
                        "authored_angle_degrees":-103,"close_delta_degrees":103},
            "authoring_notes":["Source retains editable parts and edge-radius modifiers.",
                "Export components are consolidated by function, with real glass walls and separate moving parts.",
                "Centrifuge tubes are authored balanced and stationary under an open lid.",
                "GLB packs PBR images and glass transmission; FBX materials require engine setup.",
                "ORM red is constant one; no AO bake was run.",
                "No smoke/VFX system, gameplay, UE import or build-menu registration implemented."],
            "render_performed":False,"tests_run":False,"ue_imported":False,"gameplay_registered":False}
    (ROOT/"Receipts/authoring_receipt.json").write_text(json.dumps(report,indent=2),"utf8")
    progress(json.dumps({"result":"saved","triangles":report["triangles"],"source_mesh_objects":report["source_mesh_objects"],
                         "components":len(records),"seconds":report["seconds"]}))

if __name__=="__main__":author()
