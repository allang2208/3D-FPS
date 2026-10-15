import math
from mathutils import Matrix
import geometry as H

def fuse_set():
 H.rounded('Moulded transport carrier',(0,0,.35),(8.6,9.0,.7),'plastic',.65,.07)
 H.frame('Raised perimeter lip',(0,0,.72),(8.55,8.95,.5),.22,'blacksteel',.62)
 for x in (-3.9,3.9):
  for y in (-3.95,3.95):H.screw('Carrier corner fastener',(x,y,1.01),.14)
 for x in (-1.15,1.15):H.rounded('Separator rib',(x,0,.85),(.22,7.4,.6),'rubber',.08,.03)
 for i,x in enumerate((-2.45,0,2.45)):
  for y in (-2.35,2.35):
   H.rounded('Fuse saddle insulator',(x,y,.85),(1.95,1.25,.55),'rubber',.2,.05)
   H.ring('Retaining spring collar',(x,y,1.62),.94,.85,.22,'copper','Y',64)
   H.box('Spring clip foot',(x,y,.97),(1.8,.3,.13),'copper',.035)
  H.lathe('F'+str(i+1)+' glazed ceramic body',(x,0,1.62),[(-2.72,0),(-2.72,.70),(-2.60,.79),(2.60,.79),(2.72,.70),(2.72,0)],'ceramic','Y',96)
  for side in (-1,1):
   y=side*2.78
   H.cylinder('Nickel plated end cap',(x,y,1.62),.86,.7,'steel','Y',80,.045)
   H.ring('Crimped cap seam',(x,y-side*.25,1.62),.885,.855,.055,'aluminum','Y',80)
   H.rounded('Copper blade contact',(x,side*3.46,1.62),(.72,1.20,.17),'copper',.11,.035)
   H.box('Contact blade stamp',(x,side*3.65,1.715),(.42,.12,.025),'gold',.008)
  vertices=[]
  for j in range(25):
   theta=math.radians(-48+96*j/24)
   vertices.extend([(x+.797*math.sin(theta),y,1.62+.797*math.cos(theta)) for y in (-1.75,1.75)])
  marking=H.mesh('Conformal ceramic technical marking',vertices,[(2*j,2*j+2,2*j+3,2*j+1) for j in range(24)],'fuse',True)
  marking['authored_decal']=True;u0,v0,u1,v1=H.rect('fuse')
  for loop in marking.data.loops:
   index=loop.vertex_index;marking.data.uv_layers.active.data[loop.index].uv=(u0+(u1-u0)*(index//2)/24,v0+(v1-v0)*(index%2))
  H.cylinder('Blown fuse indicator seat',(x,2.08,2.435),.16,.06,'blacksteel','Z',32,.01)
  H.cylinder('Red indicator plug',(x,2.08,2.48),.10,.055,'red','Z',32,.015)
  for y in (-1.9,1.9):H.ring('Ceramic raised shoulder',(x,y,1.62),.804,.77,.065,'ceramic','Y',80)
 for x in (-3.6,3.6):
  for y in (-3.3,0,3.3):H.box('Carrier reinforcing underside',(x,y,.12),(.38,1.05,.24),'rubber',.065)
 H.panel('Batch plate',(0,-4.2,.755),2.0,.35,'serial')
 H.COLLISIONS=[((0,0,1.35),(8.6,9,2.7))]

def power_module():
 base=H.rounded('Die cast aluminium heat spreader',(0,0,.38),(18.8,8.8,.76),'aluminum',.65,.10)
 for x in (-8.5,8.5):
  for y in (-3.65,3.65):H.cut(base,(x,y,.35),(.66,.66,2),.30)
 for i in range(17):
  y=-3.24+i*.405
  H.box('Extruded heat sink fin %02d'%i,(0,y,1.18),(16.9,.19,1.62),'aluminum',.042)
 H.rounded('Heat sink top bridge',(0,0,2.03),(17.4,7.1,.30),'aluminum',.48,.05)
 H.rounded('Thermal isolation gasket',(0,0,2.25),(16.7,6.8,.16),'rubber',.35,.03)
 H.rounded('Injection moulded power enclosure',(0,0,2.9),(16.6,6.7,1.22),'plastic',.42,.08)
 H.frame('Cover perimeter seam',(0,0,3.50),(16.30,6.45,.12),.10,'blacksteel',.32)
 H.rounded('Sealed power stage lid',(-2.75,0,3.86),(10.25,5.9,.65),'plastic',.38,.07)
 H.panel('Original power module nameplate',(-2.75,0,4.196),8.9,4.1,'module')
 for x in (-7.1,1.5):
  for y in (-2.45,2.45):H.screw('Cover recessed screw',(x,y,4.23),.21)
 # Exposed replaceable low-voltage control board beside the sealed power stage.
 H.rounded('FR4 control board',(5.45,0,3.68),(4.65,5.72,.18),'pcb',.18,.018)
 H.panel('Board tracks and component legends',(5.45,0,3.78),4.52,5.55,'pcb_art')
 for x in (3.48,7.42):
  for y in (-2.42,2.42):
   H.cylinder('Board brass standoff',(x,y,3.45),.16,.50,'gold','Z',24,.015)
   H.screw('PCB mounting screw',(x,y,3.85),.13)
 H.rounded('Controller QFP package',(5.35,-.15,4.04),(1.35,1.55,.42),'plastic',.10,.025)
 for side in (-1,1):
  for j in range(10):H.box('Tinned controller lead',(5.35+side*.77,-.73+j*.13,3.91),(.25,.055,.09),'steel',.009)
 for j in range(7):
  x=3.8+j*.48
  H.box('SMD resistor ceramic',(x,1.45,3.90),(.27,.15,.13),'ceramic',.025)
  for side in (-1,1):H.box('SMD plated terminal',(x+side*.105,1.45,3.91),(.065,.16,.14),'steel',.009)
 for x in (4.1,6.7):
  H.cylinder('Control electrolytic capacitor',(x,-1.60,4.1),.29,.61,'blacksteel','Z',48,.03)
  H.cylinder('Capacitor scored cap',(x,-1.60,4.42),.25,.025,'aluminum','Z',48,.005)
  H.box('Cap relief score X',(x,-1.60,4.437),(.40,.025,.012),'ink',.005)
  H.box('Cap relief score Y',(x,-1.60,4.437),(.025,.40,.012),'ink',.005)
 for x in (-5.6,0,5.6):
  H.rounded('Terminal insulating block',(x,-3.26,3.38),(2.65,1.65,.8),'plastic',.20,.05)
  H.rounded('Exposed copper power lug',(x,-3.40,3.85),(2.0,1.42,.18),'copper',.15,.025)
  H.ring('Terminal spring washer',(x,-3.4,4.00),.37,.18,.10,'steel','Z',48)
  H.cylinder('Terminal hexagonal head',(x,-3.4,4.11),.28,.16,'steel','Z',6,.025)
  H.screw('Terminal drive recess',(x,-3.4,4.23),.15)
 for x in (-5.6,0,5.6):H.stamp('Moulded terminal designation','U' if x<0 else 'V' if x==0 else 'W',(x,-2.28,4.23),.32,'white')
 H.frame('Keyed control connector',(5.6,3.18,3.25),(3.9,1.4,.65),.20,'plastic',.16)
 for j in range(8):H.box('Gold control connector contact',(4.20+j*.39,3.18,3.51),(.10,.9,.08),'gold',.015)
 for x in (-8.5,8.5):
  for y in (-3.65,3.65):H.ring('Mounting hole raised rim',(x,y,.80),.50,.34,.12,'steel','Z',48)
 H.panel('Bottom traceability label',(0,0,-.006),5.6,3.0,'serial','-Z')
 H.COLLISIONS=[((0,0,2.15),(18.8,8.9,4.3))]

def storage_cell():
 H.rounded('Insulating bottom shoe',(0,0,.27),(6.5,3.65,.54),'rubber',.55,.06)
 H.loft('Deep drawn aluminium can',[(.35,6.4,3.5,.55,0,0),(.55,6.4,3.5,.55,0,0),(12.32,6.4,3.5,.55,0,0),(12.55,6.22,3.35,.50,0,0)],'aluminum',20)
 for z in (.55,12.30):H.frame('Folded continuous seal seam',(0,0,z),(6.48,3.58,.13),.12,'steel',.57)
 H.rounded('Top isolation gasket',(0,0,12.57),(6.20,3.32,.16),'rubber',.47,.025)
 H.rounded('Sealed top plate',(0,0,12.72),(6.18,3.30,.22),'aluminum',.44,.06)
 for x,color in [(-1.87,'blue'),(1.87,'red')]:
  H.rounded('Terminal insulation shroud',(x,0,12.98),(1.75,2.05,.36),color,.40,.05)
  H.cylinder('Terminal sealing ceramic',(x,0,13.18),.62,.18,'ceramic','Z',72,.03)
  H.cylinder('Plated output terminal',(x,0,13.43),.46,.44,'copper','Z',72,.045)
  H.ring('Pole top washer',(x,0,13.67),.49,.22,.09,'steel','Z',64)
  H.cylinder('Pole clamping hex',(x,0,13.79),.34,.18,'steel','Z',6,.025)
  H.screw('Pole recessed drive',(x,0,13.90),.20)
 H.rounded('Pressure relief cartridge',(0,0,12.90),(1.35,1.95,.16),'blacksteel',.35,.02)
 H.rounded('Burst vent aluminium foil',(0,0,13.0),(1.05,1.55,.06),'steel',.28,.012)
 for side in (-1,1):
  o=H.box('Stamped vent diagonal',(0,0,13.035),(.025,1.13,.014),'ink',.005);o.rotation_euler.z=side*.58
 H.panel('Energy cell technical label',(0,-1.756,6.65),5.1,9.5,'cell','-Y')
 H.panel('Rear warning strip',(0,1.757,9.2),5.15,1.4,'warning','Y')
 H.panel('Rear traceability plaque',(0,1.757,4.2),3.1,3.0,'serial','Y')
 for x in (-3.20,3.20):
  for z in (2.2,3.1,4.,4.9,5.8,6.7,7.6,8.5,9.4,10.3):H.box('Pressed side stiffening bead',(x,0,z),(.045,2.25,.095),'aluminum',.02)
 H.stamp('Positive polarity mark','+',(1.87,-1.14,12.86),.45,'red')
 H.stamp('Negative polarity mark','-',(-1.87,-1.14,12.86),.45,'blue')
 for x in (-2.7,2.7):
  for y in (-1.15,1.15):H.screw('Top plate fastener',(x,y,12.86),.115)
 H.COLLISIONS=[((0,0,6.35),(6.5,3.65,12.7)),((0,0,13.15),(5.7,2.2,1.8))]

BUILDERS={'FuseSet':fuse_set,'PowerModule':power_module,'StorageCell':storage_cell}
