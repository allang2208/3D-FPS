"""Six distinct manufactured collectibles, centimetres and editable solid parts."""
import math
import geometry as H

def bolt(name,p,r=.22):
 H.ring(name+' washer',p,r*1.48,r*.70,.07,'zinc',sides=36)
 H.cylinder(name+' hex head',(p[0],p[1],p[2]+.12),r,.22,'steel',sides=6,edge=.025)
 H.stamp(name+' grade','8.8',(p[0],p[1],p[2]+.238),r*.55,'ink')

def curved_label(name,radius,z,width,height,region):
 n=48;vs=[];fs=[]
 for zz in (z-height/2,z+height/2):
  for j in range(n+1):
   t=(j/n-.5)*width/radius;vs.append((radius*math.sin(t),-radius*math.cos(t),zz))
 for j in range(n):fs.append((j,j+1,n+2+j,n+1+j))
 o=H.mesh(name,vs,fs,region,True);o['authored_decal']=True;uv=o.data.uv_layers.active;u0,v0,u1,v1=H.rect(region)
 for face in o.data.polygons:
  for li in face.loop_indices:
   index=o.data.loops[li].vertex_index;uv.data[li].uv=(u0+(index%(n+1))/n*(u1-u0),v0+(index//(n+1))*(v1-v0))
 return o

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
 curved_label('Conforming printed foil label',4.522,2.65,3.8,3.5,'RespiratorFilter')
 H.box('Tamper strip',(0,-2.05,5.95),(.65,.13,.75),'orange',.03)
 H.ring('Lid recessed seal rim',(0,0,6.195),1.87,1.72,.06,'blacksteel')
 H.stamp('Lid moulded opening instruction','OPEN',(0,-.63,6.212),.35,'ink')
 H.stamp('Lid moulded size','RF 08',(0,.5,6.212),.31,'ink')
 for z in (.24,.50,4.64,4.94):H.ring('Folded seam bead',(0,0,z),4.53,4.43,.065,'steel',sides=96)
 H.cord('Lid seal witness line',[(.55,-1.88,6.22),(.55,-1.98,6.19),(.55,-2.1,6.04)],.018,'orange')
 H.COLLISIONS.append(((0,0,3.1),(8.9,8.9,6.3)))

def ceramic():
 H.box('Steel transport cradle',(0,0,.45),(17.8,10.6,.9),'blacksteel',.13)
 for x in (-8.5,8.5):H.box('Folded cradle side flange',(x,0,2.65),(.40,10.6,4.6),'blacksteel',.07)
 for i,x in enumerate((-4.1,4.1)):
  for j,y in enumerate((-2.5,2.5)):
   H.frame('Cast refractory channel',(x,y,2.9),(7.9,4.7,4.8),.74,'ceramic_alt' if i==j else 'ceramic',.32)
   H.stamp('Stamped ceramic stock mark','RC17 / '+str(1+i*2+j),(x,y-2.01,5.33),.25,'ink')
 for y in (-4.8,4.8):
  for x in (-4.1,4.1):H.box('Insulating clamp pad',(x,y,5.34),(5.8,.68,.14),'ceramic_alt',.025)
  H.box('Spring retaining strap',(0,y,5.49),(17.6,.6,.20),'steel',.04)
  for x in (-8.5,8.5):bolt('Clamp tension bolt',(x,y,5.61),.23)
 for y in (-5.2,5.2):H.box('Bent front and rear angle',(0,y,1.20),(17.6,.32,1.9),'blacksteel',.055)
 H.box('Stock plaque backing',(0,-5.42,1.37),(6.9,.12,1.85),'aluminum',.035)
 H.panel('Proportioned refractory plaque',(0,-5.485,1.37),6.5,1.5,'CeramicModule','-Y')
 for x in (-3.35,3.35):H.screw('Plaque screw',(x,-5.495,1.37),.10,'Y')
 for x in (-8.5,8.5):
  for y in (-3.4,3.4):
   H.box('Pressed flange stiffener',(x,y,2.3),(.46,.22,3.2),'edge',.045)
   H.cord('Short cradle weld',[(x-.10,y,.92),(x,y,.98),(x+.10,y,.92)],.045,'steel')
 H.COLLISIONS.append(((0,0,2.6),(17.8,10.6,5.4)))

def thermocouple():
 H.rounded('Cast terminal head',(-12,0,3.2),(7.2,7.4,5.4),'castmetal',1.3,.13)
 H.rounded('Gasket lid',(-12,0,6.0),(7.3,7.5,.5),'blacksteel',1.3,.08)
 H.rounded('Head lid cover',(-12,0,6.3),(7.1,7.3,.35),'aluminum',1.2,.08)
 H.panel('Probe identification plate',(-12,0,6.49),4.9,4.9,'Thermocouple')
 for x in (-14.55,-9.45):
  for y in (-2.65,2.65):H.screw('Cover socket screw',(x,y,6.51),.23)
 H.cylinder('Compression fitting',(-7.5,0,3.2),1.45,2.1,'steel','X',6,.08)
 H.cylinder('Stainless probe sheath',(4.4,0,3.2),.36,22.5,'steel','X',48,.1)
 H.cylinder('Rounded probe tip',(15.65,0,3.2),.36,.55,'steel','X',48,.18)
 for x in (-6.6,-6.3,-6.0):H.ring('Fitting compression rings',(x,0,3.2),.72,.34,.17,'steel','X')
 H.cylinder('Rear lock nut',(-8.35,0,3.2),1.56,.6,'steel','X',6,.05)
 for x in (-7.0,-6.82,-6.64,-6.46,-6.28):H.ring('Machined threaded stem',(x,0,3.2),.92,.80,.07,'steel','X',48)
 H.ring('Probe laser weld',(15.55,0,3.2),.38,.34,.09,'zinc','X',48)
 H.cylinder('Cable gland',(-12,4.35,3.2),.78,2.0,'blacksteel','Y',12,.04)
 H.cord('Braided insulated sensor lead',[(-12,5,3.2),(-9,7.2,2.2),(-3,7.7,1.7),(4,6.6,1.7),(8,5.6,1.7),(9,7.5,1.7),(5,9.4,1.7),(-1,9.3,1.7),(-5,7.2,1.7)],.2,'canvas')
 for y in (4.9,5.1,5.3):H.ring('Gland sealing rib',(-12,y,3.2),.60,.37,.12,'rubber','Y',36)
 H.rounded('Sensor connector',(-5,6.5,1.7),(1.3,2.5,1.3),'orange',.2,.08)
 H.box('Connector mould split',(-5,6.5,1.7),(1.32,2.2,.045),'plastic',.015)
 H.screw('Connector terminal screw',(-5,6.8,2.37),.14)
 H.stamp('Connector polarity mark','+',(-5,5.8,2.37),.3,'ink')
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
 for z in (1.32,26.68):H.ring('Filter media potting seal',(0,0,z),5.77,3.79,.24,'adhesive',sides=96)
 for z in (.17,.34,27.67,27.83):H.ring('Rolled end cap bead',(0,0,z),6.14,5.96,.09,'aluminum',sides=96)
 for z in [1.4+k*1.1 for k in range(24)]:H.ring('Inner support cage hoop',(0,0,z),3.77,3.67,.10,'blacksteel',sides=72)
 for i in range(32):
  t=i*math.tau/32;H.cylinder('Inner support cage strut',(3.72*math.cos(t),3.72*math.sin(t),14),.045,25.2,'blacksteel',sides=8,edge=0)
 for i in range(8):
  t=i*math.tau/8;H.cylinder('Support cage rod',(5.62*math.cos(t),5.62*math.sin(t),14),.065,25.4,'steel',sides=12,edge=0)
 H.box('Manufacturer plate',(0,-5.65,14),(3.5,.14,5.6),'steel',.09)
 H.panel('Cartridge stock label',(0,-5.73,14),3.3,5.4,'IndustrialFilter','-Y')
 for z in (11.55,16.45):
  for x in (-1.47,1.47):H.screw('Filter plaque rivet',(x,-5.75,z),.085,'Y')
 H.COLLISIONS.append(((0,0,14),(12.2,12.2,28.3)))

def archive():
 H.rounded('Reinforced archive back',(0,0,.22),(30.0,22.0,.44),'canvas',.3,.04)
 for i in range(26):
  z=.52+i*.077;H.rounded('Bound record sheet %02d'%i,(.12*math.sin(i),.12*math.cos(i),z),(28.7,20.6,.065),'paper_light' if i%4==0 else 'paper',.14,.01)
 H.rounded('Cloth archive cover',(0,0,2.7),(30.0,22.0,.36),'canvas',.3,.045)
 H.rounded('Bound cloth spine',(-14.6,0,1.5),(.85,22,2.6),'canvas',.3,.06)
 H.panel('Incident dossier cover',(1.1,0,2.89),16.6,16.6,'IncidentArchive')
 for y in (-7.7,7.7):
  H.box('Woven security band',(0,y,2.94),(30.0,1.1,.12),'red',.015)
  for x in (-15.02,15.02):H.box('Band edge',(x,y,1.48),(.12,1.1,2.9),'red',.015)
  H.box('Band underside',(0,y,-.04),(30,1.1,.12),'red',.015)
 H.cylinder('Evidence wax seal',(9.5,-7.7,3.15),1.2,.3,'wax',sides=64,edge=.10)
 H.ring('Wax embossed perimeter',(9.5,-7.7,3.32),.97,.85,.075,'wax',sides=64)
 H.stamp('Stamped seal','CS',(9.5,-7.7,3.34),.55,'red')
 for x in (-13.8,13.8):
  for j in range(28):
   y=-9.9+j*.73;H.cord('Cover binding stitch',[(x-.12,y,2.88),(x,y+.18,2.91),(x+.12,y+.25,2.88)],.018,'paper')
 for y in (-10.15,10.15):H.cord('Cloth edge folded seam',[(-13.6,y,2.86),(0,y,2.87),(13.6,y,2.86)],.045,'canvas')
 H.box('Archive spine marking strip',(-15.05,0,1.50),(.04,8.0,1.5),'paper',.01)
 for x in (-14.6,14.6):
  for y in (-10.6,10.6):H.rounded('Metal corner guard',(x,y,2.94),(1.0,.9,.19),'blacksteel',.2,.03)
 H.COLLISIONS.append(((0,0,1.6),(30.2,22.1,3.5)))

def catalyst():
 H.frame('Catalyst stainless cassette',(0,0,5.2),(22.0,16.0,10.4),.65,'steel',.6)
 # Dense shared straight-through webs replace rows of rounded cup-like inserts.
 nx,ny=36,24;w,h=20.5,14.5
 for i in range(nx+1):H.box('Catalyst longitudinal ceramic web',(-w/2+i*w/nx,0,5.2),(.075,h,9.8),'ceramic_core',.012)
 for j in range(ny+1):H.box('Catalyst transverse ceramic web',(0,-h/2+j*h/ny,5.2),(w,.075,9.8),'ceramic_core',.012)
 for z in (.40,10.0):H.frame('Ceramic perimeter packing',(0,0,z),(21.05,15.05,.18),.26,'fiber',.12)
 for z in (.25,10.15):
  H.frame('Cassette rolled flange',(0,0,z),(22.8,16.8,.5),.8,'aluminum',.65)
  for x in (-10.65,10.65):
   for y in (-7.65,7.65):bolt('Frame securing bolt',(x,y,z+.27),.24)
 H.box('Side identity plate',(0,-8.08,5.2),(9,.12,6.9),'blacksteel',.08)
 H.panel('Catalyst original label',(0,-8.151,5.2),6.6,6.6,'CatalyticCore','-Y')
 for x in (-11.7,11.7):
  for y in (-3.5,3.5):H.box('Handle welded mount',(x,y,5.2),(1.4,1,1.1),'steel',.12)
  H.cord('Lift handle',[(x,-3.5,5.2),(x*1.12,-3.4,5.2),(x*1.15,0,5.2),(x*1.12,3.4,5.2),(x,3.5,5.2)],.25,'steel')
  for y in (-3.5,3.5):H.cord('Handle mount weld',[(x-.45,y-.5,5.75),(x,y-.5,5.78),(x+.45,y-.5,5.75)],.055,'zinc')
 for x in (-10.7,10.7):H.box('Folded cassette corner seam',(x,-7.9,5.2),(.23,.22,9.3),'edge',.04)
 H.COLLISIONS.append(((0,0,5.3),(27.5,16.8,11.2)))

BUILDERS={'RespiratorFilter':respirator,'CeramicModule':ceramic,'Thermocouple':thermocouple,'IndustrialFilter':industrial_filter,'IncidentArchive':archive,'CatalyticCore':catalyst}
