"""Six distinct manufactured collectibles, centimetres and editable solid parts."""
import math
import geometry as H

def respirator():
 H.lathe('Pressed sealed filter can',(0,0,0),[(0,3.9),(.22,4.3),(1,4.5),(4.8,4.5),(5.1,4.2),(5.2,0.01),(0,.01)],'blue',segments=96)
 for z in (.4,4.85):H.ring('Rolled metal seam',(0,0,z),4.6,4.32,.2,'steel',sides=96)
 H.cylinder('Threaded neck',(0,0,5.45),1.9,.65,'steel',sides=72)
 for z in (5.25,5.42,5.59):H.ring('External neck thread',(0,0,z),2.02,1.84,.09,'steel')
 H.cylinder('Sealed transport cap',(0,0,5.95),2.12,.5,'plastic')
 for i in range(36):
  t=i*math.tau/36;H.cylinder('Grip flute',(2.09*math.cos(t),2.09*math.sin(t),5.97),.075,.36,'plastic',sides=8,edge=.012)
 H.cylinder('Inlet plate',(0,0,.08),3.75,.13,'blacksteel')
 for x in range(-4,5):
  for y in range(-4,5):
   if x*x+y*y<21:H.cylinder('Intake perforation',(x*.69,y*.69,-.005),.13,.02,'ink',sides=12,edge=0)
 H.panel('Original identification label',(0,-4.505,2.65),3.8,3.5,'RespiratorFilter','-Y')
 H.box('Tamper strip',(0,-2.05,5.95),(.65,.13,.75),'orange',.03)
 H.COLLISIONS.append(((0,0,3.1),(8.9,8.9,6.3)))

def ceramic():
 H.box('Steel transport cradle',(0,0,.45),(17.8,10.6,.9),'blacksteel',.13)
 for x in (-8.5,8.5):H.box('Cradle retaining flange',(x,0,2.2),(.6,10.6,3.6),'steel',.09)
 for x in (-4.1,4.1):
  for y in (-2.5,2.5):
   H.frame('Refractory through-channel',(x,y,2.9),(7.9,4.7,4.8),.74,'ceramic',.8)
 for y in (-4.8,4.8):
  H.box('Metal retaining strap',(0,y,5.1),(16.6,.55,.23),'steel',.045)
  for x in (-8.3,8.3):H.screw('Cradle rivet',(x,y,5.21),.19)
 H.panel('Ceramic spare stock label',(0,-5.312,.47),6.0,.7,'CeramicModule','-Y')
 H.stamp('Ceramic batch mark','RC / 17',(0,-4.3,5.32),.47,'ink')
 H.COLLISIONS.append(((0,0,2.6),(17.8,10.6,5.4)))

def thermocouple():
 H.rounded('Cast terminal head',(-12,0,3.2),(7.2,7.4,5.4),'aluminum',1.3,.13)
 H.rounded('Gasket lid',(-12,0,6.0),(7.3,7.5,.5),'blacksteel',1.3,.08)
 H.rounded('Head lid cover',(-12,0,6.3),(7.1,7.3,.35),'aluminum',1.2,.08)
 H.panel('Probe identification plate',(-12,0,6.49),4.9,4.9,'Thermocouple')
 for x in (-14.55,-9.45):
  for y in (-2.65,2.65):H.screw('Cover socket screw',(x,y,6.51),.23)
 H.cylinder('Compression fitting',(-7.5,0,3.2),1.45,2.1,'steel','X',6,.08)
 H.cylinder('Stainless probe sheath',(4.4,0,3.2),.36,22.5,'steel','X',48,.1)
 H.cylinder('Rounded probe tip',(15.65,0,3.2),.36,.55,'steel','X',48,.18)
 for x in (-6.6,-6.3,-6.0):H.ring('Fitting compression rings',(x,0,3.2),.72,.34,.17,'steel','X')
 H.cylinder('Cable gland',(-12,4.35,3.2),.78,2.0,'blacksteel','Y',12,.04)
 H.cord('Braided insulated sensor lead',[(-12,5,3.2),(-9,7.2,2.2),(-3,7.7,1.7),(4,6.6,1.7),(8,5.6,1.7),(9,7.5,1.7),(5,9.4,1.7),(-1,9.3,1.7),(-5,7.2,1.7)],.2,'canvas')
 H.rounded('Sensor connector',(-5,6.5,1.7),(1.3,2.5,1.3),'orange',.2,.08)
 for x in (-5.33,-4.67):H.box('Connector contact pin',(x,4.95,1.7),(.18,.8,.5),'copper',.03)
 H.COLLISIONS.extend([((-12,0,3.3),(7.4,7.6,6.5)),((4.5,0,3.2),(24,.85,.85)),((-1.7,7.4,1.7),(23,4,1.8))])

def industrial_filter():
 # Alternating radii form actual pleats with closed inner/outer shells.
 n=128;verts=[];faces=[]
 for z,inner in ((1.2,False),(26.8,False),(26.8,True),(1.2,True)):
  for j in range(n):
   r=3.8 if inner else 5.6 if j%2==0 else 4.6;t=j*math.tau/n;verts.append((r*math.cos(t),r*math.sin(t),z))
 for k in range(4):
  for j in range(n):q=(j+1)%n;faces.append((k*n+j,k*n+q,((k+1)%4)*n+q,((k+1)%4)*n+j))
 H.mesh('Continuous pleated filter media',verts,faces,'fiber')
 for z in (.65,27.35):
  H.ring('Stamped metal end cap',(0,0,z),6.1,3.6,1.3,'steel',sides=96)
  H.ring('Sealing gasket',(0,0,z+(.72 if z>10 else -.72)),5.9,3.75,.22,'rubber',sides=96)
 for z in (6.0,14.0,22.0):H.ring('Pleat support hoop',(0,0,z),5.72,5.46,.28,'steel',sides=96)
 for i in range(8):
  t=i*math.tau/8;H.cylinder('Support cage rod',(5.62*math.cos(t),5.62*math.sin(t),14),.065,25.4,'steel',sides=12,edge=0)
 H.box('Manufacturer plate',(0,-5.65,14),(3.5,.14,5.6),'steel',.09)
 H.panel('Cartridge stock label',(0,-5.73,14),3.3,5.4,'IndustrialFilter','-Y')
 H.COLLISIONS.append(((0,0,14),(12.2,12.2,28.3)))

def archive():
 H.rounded('Reinforced archive back',(0,0,.22),(30.0,22.0,.44),'canvas',.3,.04)
 for i in range(26):
  z=.52+i*.077;H.rounded('Bound record sheet %02d'%i,(.12*math.sin(i),.12*math.cos(i),z),(28.7,20.6,.065),'paper',.14,.01)
 H.rounded('Cloth archive cover',(0,0,2.7),(30.0,22.0,.36),'canvas',.3,.045)
 H.rounded('Bound cloth spine',(-14.6,0,1.5),(.85,22,2.6),'canvas',.3,.06)
 H.panel('Incident dossier cover',(1.1,0,2.89),16.6,16.6,'IncidentArchive')
 for y in (-7.7,7.7):
  H.box('Woven security band',(0,y,2.94),(30.0,1.1,.12),'red',.015)
  for x in (-15.02,15.02):H.box('Band edge',(x,y,1.48),(.12,1.1,2.9),'red',.015)
  H.box('Band underside',(0,y,-.04),(30,1.1,.12),'red',.015)
 H.cylinder('Evidence seal',(9.5,-7.7,3.15),1.2,.3,'red',sides=48,edge=.07)
 H.stamp('Stamped seal','CS',(9.5,-7.7,3.32),.6,'paper')
 for x in (-14.6,14.6):
  for y in (-10.6,10.6):H.rounded('Metal corner guard',(x,y,2.94),(1.0,.9,.19),'blacksteel',.2,.03)
 H.COLLISIONS.append(((0,0,1.6),(30.2,22.1,3.5)))

def catalyst():
 H.frame('Catalyst stainless cassette',(0,0,5.2),(22.0,16.0,10.4),.65,'steel',.6)
 # Open ceramic channels with real thickness; block remains readable from both ends.
 for i in range(17):
  for j in range(11):
   H.frame('Catalytic ceramic channel',((i-8)*1.18,(j-5)*1.27,5.2),(1.14,1.23,9.8),.13,'ceramic',.14)
 for z in (.25,10.15):
  H.frame('Cassette rolled flange',(0,0,z),(22.8,16.8,.5),.8,'aluminum',.65)
  for x in (-10.65,10.65):
   for y in (-7.65,7.65):H.screw('Frame securing bolt',(x,y,z+.27),.24)
 H.box('Side identity plate',(0,-8.08,5.2),(9,.12,6.9),'blacksteel',.08)
 H.panel('Catalyst original label',(0,-8.151,5.2),6.6,6.6,'CatalyticCore','-Y')
 for x in (-11.7,11.7):
  for y in (-3.5,3.5):H.box('Handle welded mount',(x,y,5.2),(1.4,1,1.1),'steel',.12)
  H.cord('Lift handle',[(x,-3.5,5.2),(x*1.12,-3.4,5.2),(x*1.15,0,5.2),(x*1.12,3.4,5.2),(x,3.5,5.2)],.25,'steel')
 H.COLLISIONS.append(((0,0,5.3),(27.5,16.8,11.2)))

BUILDERS={'RespiratorFilter':respirator,'CeramicModule':ceramic,'Thermocouple':thermocouple,'IndustrialFilter':industrial_filter,'IncidentArchive':archive,'CatalyticCore':catalyst}
