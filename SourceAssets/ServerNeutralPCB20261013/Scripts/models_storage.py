"""Memory, NIC, drives and processor models for the authored server loot set."""
import bpy
import mesh_helpers as H
from hardware_parts import *

def ram():
    board=pcb('ECC memory laminate',(0,0,.25),(13.8,3.0,.16),[
        ((.50,-1.47,.25),(.28,.48,.65)),
        ((-6.87,.72,.25),(.30,.37,.65)),((6.87,.72,.25),(.30,.37,.65))])
    edge_contacts('Memory gold finger',-6.66,-1.15,.25,13.32,144,.64,(.30,.69))
    for side in (-1,1):
        for j in range(9):
            x=-5.78+j*1.445
            chip('Memory package',(x,.35,.25+side*.16),1.20,1.48,.15,mark=side>0)
    chip('Register controller',(.38,-.66,.40),.73,.56,.15)
    for x in (-5.83,-4.38,-2.93,-1.48,1.41,2.86,4.31,5.76):
        smd('Decoupling capacitor',(x,1.26,.375),(.23,.11,.07))
        smd('Memory termination',(x,-.62,.375),(.16,.10,.055),'chip')
    box('Serial paper backing',(3.82,.36,.51),(3.83,1.66,.019),'paper',.018,2)
    panel('Memory capacity serial',(3.82,.36,.522),3.69,1.58,'secondary')
    for x in (-6.58,6.58):plated_hole(board,'Memory tooling pad',x,1.11,.25,.085)

def nic():
    board=pcb('Server NIC PCB',(.37,0,.25),(14.1,7.70,.16),[
        ((-2.73,-3.80,.25),(.30,.83,.65))])
    edge_contacts('NIC edge connector',-4.15,-3.37,.25,5.52,58,.65,(-2.91,-2.55))
    bracket=box('NIC formed bracket',(-6.91,0,1.0),(.15,7.90,1.97),'steel',.05,3)
    for y in (-2.14,1.11):
        cut(bracket,(-6.91,y,1.11),(.50,2.03,1.53))
        port_x('Shielded network socket',(-5.72,y,1.09),2.63,2.0,1.54,-1,'steel',8)
        for yy,region in ((y-.69,'indicator'),(y+.69,'white')):
            box('Network link lens',(-7.071,yy,1.76),(.046,.18,.12),region,.024,3)
    box('NIC bracket fixing lip',(-6.62,3.76,1.91),(.72,.38,.12),'steel',.036,3)
    round_cut(bracket,(-6.91,3.12,.93),.17,.65,'X')
    chip('NIC controller package',(.5,.5,.409),2.90,2.90,.158,False)
    heat_sink('NIC controller heatsink',(.5,.5,.46),3.5,3.4,1.10,15,'aluminum')
    for x in (-1.46,2.45):
        for y in (-1.40,2.40):
            cyl('NIC spring fixing',(x,y,.57),.14,.34,'plastic',sides=24,radius=.018)
    chip('NIC flash device',(5.15,1.74,.47),1.65,1.27,.25)
    chip('NIC oscillator',(4.84,-1.01,.48),1.12,.81,.28)
    cap_row('NIC capacitors',3.53,-2.24,.40,11,.31)
    cap_row('NIC bias components',3.84,2.89,.40,9,.31)
    for x in (-3.78,-2.87):
        cyl('NIC polymer capacitor',(x,2.79,.71),.26,.79,'aluminum',sides=28,radius=.025)
        cyl('Capacitor dark vent',(x,2.79,1.12),.215,.016,'chip',sides=24,radius=0)
    for x,y in ((6.73,3.27),(6.73,-3.10),(-3.3,3.24)):
        plated_hole(board,'NIC plated fixing',x,y,.25,.14)
    box('NIC label substrate',(4.71,.02,.342),(2.30,1.04,.017),'paper',.012,2)
    panel('NIC inventory sticker',(4.71,.02,.352),2.22,.95,'primary')

def hdd():
    base=box('Cast hard drive chassis',(0,0,1.33),(14.72,10,2.42),'plastic',.23,5)
    cut(base,(2.4,0,.16),(8.35,8.1,.75))
    cover=box('Stamped hard drive cover',(0,0,2.605),(14.74,9.98,.25),'steel',.19,5)
    box('Drive cover parting gasket',(0,0,2.446),(14.69,9.96,.060),'rubber',.14,3)
    for y in (-4.55,4.55):box('Cover stamped edge rib',(0,y,2.763),(12.92,.12,.10),'aluminum',.045,4)
    cyl('Shallow stamped spindle dish',(-5.01,0,2.755),1.83,.058,'aluminum',sides=72,radius=.045)
    ring('Spindle dish rolled bead',(-5.01,0,2.78),1.85,1.77,.032,'steel',sides=72)
    box('Hard drive label stock',(1.34,0,2.747),(8.67,7.88,.03),'paper',.055,3)
    panel('Hard drive specification print',(1.34,1.54,2.765),8.38,3.59,'primary')
    panel('Hard drive inventory print',(1.34,-1.05,2.765),8.38,2.16,'secondary')
    panel('Hard drive serial strip',(1.34,-3.00,2.765),8.38,1.12,'barcode')
    for x,y in ((-6.65,-4.15),(-6.65,4.15),(6.65,-4.15),(6.65,4.15),(0,-4.25),(0,4.25)):
        cyl('Cover countersink',(x,y,2.744),.28,.025,'plastic',sides=28,radius=.014)
        H.screw('Hard drive cover screw',(x,y,2.77),.16)
    control=pcb('Hard drive underside control board',(2.50,0,.343),(7.91,7.58,.13))
    # Underside chips face outward into the cast chassis recess.
    chip('Underside drive controller',(1.25,-1.35,.187),1.80,1.80,.17,False)
    chip('Underside drive cache',(3.90,1.40,.187),1.62,1.12,.17,False)
    for x in (.0,5.60):
        for y in (-3.32,3.32):plated_hole(control,'Drive PCB mounting annulus',x,y,.343,.12)
    sata_end(7.03,.73,6.7)
    for y in (-5.006,5.006):
        for x in (-5.40,0,5.40):
            cyl('Side mounting recess',(x,y,1.35),.20,.014,'chip','Y',28,0)
            cyl('Side tapped seat',(x,y+( .011 if y>0 else -.011),1.35),.108,.018,'steel','Y',24,0)

def ssd():
    base=box('SSD lower aluminum shell',(0,0,.29),(9.95,6.95,.57),'plastic',.14,5)
    cut(base,(4.74,0,.31),(.81,6.52,.82))
    box('SSD satin aluminum lid',(0,0,.702),(9.98,6.98,.25),'aluminum',.14,5)
    box('SSD assembly seam',(0,0,.566),(9.94,6.94,.040),'rubber',.10,3)
    box('SSD upper label stock',(-.52,0,.840),(7.40,5.48,.023),'paper',.045,3)
    panel('SSD capacity panel',(-.52,.82,.854),7.15,3.06,'primary')
    panel('SSD serialized strip',(-.52,-1.91,.854),7.15,1.20,'barcode')
    sata_end(4.54,.29,6.43)
    for x in (-4.52,3.91):
        for y in (-2.96,2.96):H.screw('SSD captive screw',(x,y,.84),.113)
    panel('SSD underside stock label',(-.12,0,-.006),6.4,2.74,'secondary','BOTTOM')

def cpu():
    # Open-centre transport frame protects the package while exposing its underside.
    carrier=box('Antistatic CPU transport frame',(0,0,.43),(6,6,.86),'plastic',.19,5)
    cut(carrier,(0,0,.43),(5.40,5.40,1.9))
    substrate=pcb('Server processor package',(0,0,.35),(5.38,5.38,.18))
    lid=box('Nickel plated heat spreader',(0,0,.60),(4.67,4.67,.34),'steel',.18,6)
    for x in (-1,1):
        for y in (-1,1):
            cut(lid,(x*2.24,y*2.24,.60),(.29,.29,.8))
            box('Transport corner retaining tab',(x*2.60,y*2.60,.78),(.50,.50,.15),'plastic',.09,3)
    # Low profile contact lands are readable when viewed through the frame opening.
    for i in range(18):
        for j in range(18):
            x=(i-8.5)*.25;y=(j-8.5)*.25
            if abs(x)<.53 and abs(y)<.53:continue
            box('Processor contact land',(x,y,.245),(.157,.157,.017),'gold',0)
    for x in (-2.55,2.55):
        for j in range(9):smd('Package bypass capacitor',(x,-1.77+j*.43,.473),(.17,.10,.055))
    panel('Processor etched identity',(0,.17,.776),3.85,1.10,'etch')
    box('Pin one orientation mark',(-2.42,-2.40,.452),(.23,.23,.022),'gold',0)

BUILDERS={'RAM':ram,'NIC':nic,'HDD':hdd,'SSD':ssd,'CPU':cpu}
