"""Original graphics, RAID and passive-compute card structures."""
import math
import mesh_helpers as H
from hardware_parts import *

def card_bracket(name,x,width,height,ports=False):
    plate=box(name,(x,0,height*.5),(.15,width,height),'steel',.065,3)
    for y in (-width*.5+.30,width*.5-.30):
        box(name+' fixing return',(x+.29,y,height-.08),(.72,.40,.16),'steel',.035,3)
    for y in (-3.6,-2.4,-1.2,0,1.2,2.4,3.6):
        cut(plate,(x,y,height*.77),(.48,.79,height*.23))
    if ports:
        for j,y in enumerate((-3.85,-1.30,1.25,3.80)):
            cut(plate,(x,y,1.02),(.50,1.83,.82))
            port_x('Video connector '+str(j),(x+.63,y,1.02),1.40,1.83,.87,-1,'steel',10)
    return plate

def gpu():
    board=pcb('Graphics card PCB',(0,0,.39),(27.40,10.72,.18),[
        ((-6.1,-5.33,.39),(.26,.70,.8))])
    edge_contacts('Graphics edge gold finger',-9.65,-5.54,.39,12.78,100,.72,(-6.28,-5.92))
    box('Graphics structural backplate',(0,.17,.12),(27.36,10.62,.17),'plastic',.23,5)
    for x in (-11.75,-3.35,3.35,11.75):
        for y in (-4.63,4.70):H.screw('Backplate standoff screw',(x,y,.242),.11)
    chip('Graphics processor package',(0,0,.59),4.45,4.45,.23,False)
    heat_sink('Graphics fin stack',(0,.22,.70),24.72,9.00,1.68,42,'aluminum','X')
    # Pipes run along the outer fin face and return into the cold plate region.
    for j in range(3):
        yy=4.22+j*.22;zz=.88+j*.25
        H.cord('Copper thermal pipe',[(-10.4,yy,zz),(-11.2,yy,zz+.40),(-9.8,yy,zz+.60),(0,yy,zz+.61),(10.0,yy,zz+.58),(11.0,yy,zz+.12)],.14,'copper')
    shroud=box('Dual fan protective shroud',(0,.18,3.02),(27.78,11.2,1.74),'plastic',.29,6)
    # Hollow under the faceplate, then cut both full-depth circular fan openings.
    cut(shroud,(0,.18,2.41),(26.75,10.24,1.47))
    for x in (-6.64,6.64):
        round_cut(shroud,(x,.27,3.0),4.85,3.8)
        fan('Graphics cooling fan',(x,.27,3.36),4.66,11)
        for y in (-4.57,5.11):box('Fan motor frame support',(x,y,2.85),(.21,.71,.22),'plastic',.035,3)
    # Raised edging carries readable contrast without rarity-colored paint.
    for y in (-5.19,5.52):box('Shroud rim accent',(0,y,3.72),(25.70,.15,.12),'steel',.045,3)
    for x in (-12.77,0,12.77):
        for y in (-4.75,5.04):H.screw('Graphics shroud screw',(x,y,3.92),.12)
    power_socket('Graphics auxiliary power',(10.10,-5.00,1.17),2.52,1.30,1.32)
    card_bracket('Dual slot graphics bracket',-13.98,11.54,3.92,True)
    panel('Graphics model side plate',(1.18,-5.430,2.27),10.9,1.08,'silkscreen','FRONT')
    panel('Graphics back serial',(4.63,.12,.024),7.7,1.445,'barcode','BOTTOM')

def raid():
    board=pcb('Array controller main PCB',(0,0,.30),(17.70,11.74,.18),[
        ((-3.73,-5.83,.30),(.28,.74,.8))])
    edge_contacts('Array controller edge fingers',-6.70,-5.50,.30,8.42,76,.68,(-3.92,-3.55))
    bracket=box('Array controller mounting bracket',(-8.98,0,1.25),(.15,11.86,2.50),'steel',.05,3)
    for y in (-4.50,-3.00,-1.50,0,1.50,3.00,4.50):cut(bracket,(-8.98,y,1.42),(.6,.94,.75))
    box('Array bracket return',(-8.68,5.52,2.43),(.72,.47,.14),'steel',.035,3)
    chip('Array controller package',(-3.3,.1,.45),3.61,3.61,.14,False)
    heat_sink('Array processor heatsink',(-3.3,.1,.49),5.02,5.44,1.67,20,'aluminum')
    for x in (-6.13,-.48):
        for y in (-2.97,3.16):cyl('Array heat sink fixing',(x,y,.63),.17,.40,'plastic',sides=24,radius=.02)
    for x in (1.15,5.39):
        for y in (-1.84,1.85):cyl('Cache daughterboard standoff',(x,y,.72),.17,.66,'gold',sides=24,radius=.015)
    cache=pcb('Array cache daughterboard',(3.28,0,1.08),(4.64,4.13,.14))
    for x in (2.18,4.36):
        for y in (-.99,.99):chip('Array cache memory',(x,y,1.29),1.65,1.24,.25)
    for x in (1.15,5.39):
        for y in (-1.84,1.85):H.screw('Cache board captive screw',(x,y,1.18),.104)
    for y in (-4.15,4.15):
        port_x('Internal array data socket',(7.10,y,1.18),2.87,2.71,1.48,1,'steel',12)
        box('Array connector release latch',(7.13,y,2.04),(1.60,.43,.20),'plastic',.04,3)
    box('Cache reserve module',(3.03,4.24,1.08),(4.34,1.34,1.32),'plastic',.15,4)
    panel('Cache reserve module marking',(3.03,4.24,1.748),3.82,1.05,'chipmark')
    chip('Array flash chip',(3.27,-4.00,.57),2.62,1.02,.27)
    cap_row('Array bias capacitor',-.37,-4.73,.465,16,.31)
    cap_row('Array memory capacitor',1.18,2.43,.465,13,.32)
    for x,y in ((-7.54,4.79),(-7.54,-4.66),(5.56,5.30),(5.56,-5.30)):
        plated_hole(board,'Array mounting annulus',x,y,.30,.17)
    panel('Array serialized identity',(-3.41,4.54,.405),5.06,2.17,'primary')

def compute():
    board=pcb('Compute accelerator PCB',(0,0,.39),(29.06,11.08,.18),[
        ((-7.22,-5.51,.39),(.28,.8,.8))])
    edge_contacts('Compute bus gold fingers',-10.42,-5.66,.39,12.56,100,.74,(-7.41,-7.03))
    box('Compute carrier backplate',(0,0,.135),(29.42,11.25,.24),'steel',.23,5)
    chip('Compute processor package',(-1.20,0,.58),5.60,5.60,.23,False)
    heat_sink('Compute passive fin bank',(-1.20,.18,.66),25.50,10.14,3.61,45,'aluminum','X')
    for y in (-5.40,5.55):
        rail=box('Compute protective side rail',(0,y,2.76),(29.68,.23,4.03),'plastic',.15,4)
        if y<0:cut(rail,(13.0,y,1.18),(2.8,1.0,1.65))
        box('Compute upper retaining rail',(0,y,4.82),(29.12,.36,.18),'steel',.055,3)
    # A slim central service spine leaves most of the actual air channels exposed.
    box('Compute top service spine',(0,.14,4.57),(28.48,2.00,.18),'plastic',.13,4)
    for x in (-13.10,13.10):
        box('Compute end brace',(x,.18,4.55),(1.44,10.55,.18),'steel',.065,3)
        for y in (-4.8,4.97):H.screw('Compute heat sink frame screw',(x,y,4.68),.14)
    card_bracket('Compute ventilated mounting bracket',-14.96,11.86,4.91,False)
    # Open-ended fins provide a real airflow tunnel; there are no decorative fans.
    power_socket('Compute auxiliary power',(13.00,-4.80,1.18),2.48,1.43,1.34)
    panel('Compute side serial',(0,-5.523,2.73),14.6,1.60,'silkscreen','FRONT')
    panel('Compute upper identity',(0,.15,4.666),8.10,1.52,'barcode')
    panel('Compute backplate inventory',(4.90,0,.009),8.98,3.85,'secondary','BOTTOM')
    for x in (-12.72,-7.0,0,7.0,12.72):
        for y in (-4.94,4.94):
            cyl('Backplate flush fixing',(x,y,.009),.17,.018,'plastic',sides=28,radius=0)

BUILDERS={'GPU':gpu,'RAID':raid,'Compute':compute}
