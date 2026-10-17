"""Four original close-range manufactured collectibles, all dimensions in centimetres."""
import math
import bpy
from mathutils import Matrix,Vector
import geometry as H
MATS={};LID_OBJECTS=[];LID_PIVOT=(0,9.55,1.65)
GLASS={
 'GlassClear':([.99,.995,1],.035,[.97,.99,1]),
 'GlassSmoked':([.22,.25,.29],.09,[.57,.64,.68]),
 'PerfumeLiquid':([.75,.42,.13],.035,[.96,.80,.51])}
def init(key):
 global MATS,LID_OBJECTS
 H.PARTS=[];H.COLLISIONS=[];H.MAT=H.material(key);MATS={'Surface':H.MAT};LID_OBJECTS=[]
 for name,(base,rough,tint) in GLASS.items():
  m=bpy.data.materials.new('M_Living_'+name);m.use_nodes=True
  p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*tint,1)
  p.inputs['Roughness'].default_value=rough;p.inputs['Transmission Weight'].default_value=1
  p.inputs['IOR'].default_value=1.36 if name=='PerfumeLiquid' else 1.48
  MATS[name]=m
def assign(o,name):o.data.materials.clear();o.data.materials.append(MATS[name]);return o
def turn(o,axis,angle):o.rotation_euler['XYZ'.index(axis)]=angle;return o
def socket_frame(name,p,w,h,depth,wall=.05,region='steel',axis='-Y',radius=.15):
 start=len(H.PARTS)
 H.frame(name,(0,0,0),(w,h,depth),wall,region,radius)
 matrix=Matrix.Identity(4)
 if axis in ('-Y','Y'):matrix=Matrix.Rotation(math.pi/2 if axis=='-Y' else -math.pi/2,4,'X')
 elif axis in ('X','-X'):matrix=Matrix.Rotation(math.pi/2 if axis=='X' else -math.pi/2,4,'Y')
 H.transform_since(start,Matrix.Translation(p)@matrix)
 return H.PARTS[-1]
def grille(name,p,cols,rows,pitch,radius,region='blacksteel',depth=.035):
 # Every hole is a real aperture into a recessed cavity, with an inner side wall.
 verts=[];faces=[]
 ring=[(-1,-1),(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0)]
 for iy in range(rows):
  for ix in range(cols):
   x=p[0]+(ix-(cols-1)/2)*pitch;y=p[1]+(iy-(rows-1)/2)*pitch;z=p[2];n=len(verts)
   for dx,dy in ring:verts.append((x+dx*pitch/2,y+dy*pitch/2,z))
   for zz in (z,z-depth):
    for dx,dy in ring:
     a=math.atan2(dy,dx);verts.append((x+radius*math.cos(a),y+radius*math.sin(a),zz))
   for j in range(8):
    k=(j+1)%8;faces.extend(((n+j,n+k,n+8+k,n+8+j),(n+8+j,n+8+k,n+16+k,n+16+j)))
 return H.mesh(name,verts,faces,region)
def knurl(name,p,r,h,count=48,axis='Z',region='edge'):
 start=len(H.PARTS);H.cylinder(name+' core',(0,0,0),r-.025,h,region,sides=64,edge=.025)
 for i in range(count):
  a=i*math.tau/count;o=H.box(name+' machined flute %02d'%i,(r*math.cos(a),r*math.sin(a),0),(.045,.07,h*.82),region,.012);o.rotation_euler.z=a
 mat=Matrix.Identity(4)
 if axis=='X':mat=Matrix.Rotation(math.pi/2,4,'Y')
 elif axis=='Y':mat=Matrix.Rotation(math.pi/2,4,'X')
 H.transform_since(start,Matrix.Translation(p)@mat)
def glass_lens(name,p,r,h):
 # Opaque multilayer coating for a recessed camera lens keeps the device Nanite-compatible.
 return H.lathe(name,p,[(-h/2,.001),(-h*.5,r*.92),(0,r),(h*.30,r*.88),(h*.55,r*.50),(h*.62,.001)],'blueglass','Y',96)
def perfume():
 shell=H.loft('Continuous crystal bottle outer and inner walls',[
  (.15,5.65,3.65,.65,0,0),(.45,6.10,4.10,.72,0,0),(.95,6.20,4.20,.74,0,0),
  (7.8,6.20,4.20,.74,0,0),(8.35,5.82,3.90,.78,0,0),(9.15,2.35,2.35,.66,0,0),(9.8,1.9,1.9,.6,0,0),
  (9.8,1.48,1.48,.48,0,0),(9.12,1.90,1.90,.55,0,0),(8.05,5.48,3.48,.68,0,0),
  (1.02,5.48,3.48,.68,0,0)],'glass',n=20);assign(shell,'GlassClear')
 fill=H.loft('Separate amber perfume with curved meniscus',[(1.06,5.40,3.40,.66,0,0),(6.9,5.40,3.40,.66,0,0),(6.965,5.40,3.40,.66,0,0),(6.935,5.32,3.32,.64,0,0)],'liquid',n=20);assign(fill,'PerfumeLiquid')
 H.cord('Atomizer dip tube',[(.15,0,9.8),(.13,0,5.5),(.5,0,1.25)],.055,'white',6)
 H.ring('Crimped pump ferrule',(0,0,9.58),1.19,.87,.52,'gold',sides=96)
 for z in (9.36,9.49,9.72,9.81):H.ring('Ferrule rolled seam',(0,0,z),1.23,1.13,.065,'gold',sides=96)
 for i in range(40):
  a=math.tau*i/40;H.cylinder('Crimp tool witness',(1.187*math.cos(a),1.187*math.sin(a),9.56),.024,.25,'bronze',sides=8,edge=.005)
 H.cylinder('Pump stem',(0,0,10.02),.33,.56,'steel',sides=48)
 H.rounded('Atomizer push button',(0,0,10.43),(1.65,1.55,.65),'gold',.42,.07)
 H.ring('Spray nozzle with bore',(0,-.79,10.43),.17,.075,.13,'steel','Y',48)
 H.cylinder('Nozzle inner shadow',(0,-.73,10.43),.072,.02,'ink','Y',24,0)
 # A smoked transparent cap exposes the internal gold atomizer without loose parts.
 cap=H.lathe('Faceted hollow smoked cap',(0,0,0),[(9.82,1.55),(12.40,1.55),(12.64,1.34),(12.64,.01),(12.36,.01),(12.36,1.27),(9.82,1.27)],'glass',segments=12)
 assign(cap,'GlassSmoked')
 H.ring('Cap satin metal bottom trim',(0,0,9.91),1.57,1.27,.18,'gold',sides=96)
 H.rounded('Cotton paper label backing',(0,-2.115,4.70),(3.96,.035,5.28),'paper',.08,.006)
 H.panel('Original perfumery printed label',(0,-2.138,4.70),3.83,5.12,'Perfume','-Y')
 H.stamp('Bottle bottom batch engraving','CS 07 / 261016',(0,.05,.14),.23,'silverfoil',rot=(math.pi,0,0))
 H.COLLISIONS=[((0,0,4.7),(6.2,4.2,9.2)),((0,0,11),(3.15,3.15,3.3))]
def laptop():
 global LID_OBJECTS
 lower=H.rounded('CNC aluminum lower chassis',(0,0,.83),(32.1,21.8,1.20),'aluminum',.78,.16)
 deck=H.rounded('Anodized palmrest and keyboard deck',(0,0,1.49),(32.05,21.75,.20),'aluminum',.78,.04)
 H.cut(deck,(0,2.6,1.5),(25.7,10.65,.72),.35)
 H.cut(lower,(0,2.6,1.54),(25.7,10.65,1.02),.35)
 H.rounded('Recessed keyboard backplate',(0,2.6,1.08),(25.45,10.45,.20),'blacksteel',.29,.025)
 rows=[['ESC','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12'],
 ['`','1','2','3','4','5','6','7','8','9','0','-','='],
 ['TAB','Q','W','E','R','T','Y','U','I','O','P','[',']'],
 ['CAPS','A','S','D','F','G','H','J','K','L',';','ENTER'],
 ['SHIFT','Z','X','C','V','B','N','M',',','.','/','SHIFT']]
 for iy,row in enumerate(rows):
  y=6.91-iy*1.72;w=24.6/len(row)
  for ix,label in enumerate(row):
   x=-12.3+w*(ix+.5);H.rounded('Independent keycap '+label,(x,y,1.42),(w-.16,1.43,.29),'keycap',.14,.055)
   H.stamp('Laser key legend '+label,label,(x,y-.06,1.573),.23 if len(label)>1 else .34,'white')
   if label in ('F','J'):H.box('Tactile home key bar',(x,y-.46,1.59),(.36,.055,.035),'white',.012)
 for x,w,t in [(-11.5,1.7,'CTRL'),(-9.55,1.7,'FN'),(-7.6,1.7,'ALT'),(-.7,11.6,''),(6.6,1.6,'ALT'),(8.45,1.6,'CTRL'),(10.25,1.6,'<'),(12.08,1.6,'>')]:
  H.rounded('Bottom row '+(t or 'spacebar'),(x,-1.70,1.42),(w,1.43,.29),'keycap',.14,.05)
  if t:H.stamp('Bottom legend '+t,t,(x,-1.74,1.575),.21,'white')
 H.rounded('Trackpad dark gasket',(0,-6.28,1.606),(10.65,6.10,.04),'ink',.33,.008)
 H.rounded('Etched glass precision trackpad',(0,-6.28,1.634),(10.50,5.95,.035),'screen',.30,.008)
 # Speaker wells and true perforated faces alongside the keyboard.
 for side in (-1,1):
  x=side*14.2;H.cut(deck,(x,2.8,1.5),(1.38,8.8,.65),.15)
  H.cut(lower,(x,2.8,1.52),(1.38,8.8,.65),.15)
  H.box('Speaker acoustic chamber',(x,2.8,1.15),(1.34,8.75,.10),'ink',.04)
  grille('Perforated speaker grille',(x,2.8,1.58),4,28,.30,.087,'blacksteel')
 # Side apertures are cut through actual chassis, with recessed sockets and contact tongues.
 for side,y,w,h,kind in [(-1,6.6,1.45,.58,'USB-A'),(-1,3.5,1.05,.42,'USB-C'),(-1,.8,1.42,.54,'HDMI'),(1,6.1,1.45,.58,'USB-A'),(1,2.0,2.20,.30,'SD')]:
  H.cut(lower,(side*15.95,y,.90),(.92,w,h),.08)
  socket_frame(kind+' folded shell',(side*16.04,y,.90),h,w,.23,.035,'steel','X',.10)
  H.box(kind+' recessed cavity',(side*15.65,y,.90),(.08,w*.91,h*.82),'ink',.015)
  H.box(kind+' contact tongue',(side*15.82,y,.83),(.28,w*.75,.055),'navy',.01)
  for q in range(4 if kind!='SD' else 7):H.box(kind+' gold contact',(side*15.86,y-w*.29+q*w*.58/(3 if kind!='SD' else 6),.866),(.17,.055,.008),'gold',.002)
 H.cut(lower,(15.97,-1.25,.9),(.88,.52,.52),.20)
 H.ring('Headphone jack metal socket',(16.06,-1.25,.9),.23,.145,.25,'steel','X',48)
 H.cylinder('Headphone jack interior',(15.8,-1.25,.9),.145,.02,'ink','X',32,0)
 H.panel('Bottom serial and power plate',(0,1,.217),9.6,3.84,'Laptop','-Z')
 for x in (-13.5,13.5):
  for y in (-8.65,8.65):
   H.rounded('Moulded non-slip foot',(x,y,.14),(3.1,.70,.27),'rubber',.30,.045)
 for x,y in [(-14.1,-9.3),(14.1,-9.3),(-14.1,9.1),(14.1,9.1),(-5.2,-9.3),(5.2,-9.3),(-5.2,8.3),(5.2,8.3)]:
  H.screw('Service screw',(x,y,.21),.13)
 for x in (-11.65,11.65):
  H.cylinder('Screen hinge barrel',(x,9.55,1.67),.39,4.2,'blacksteel','X',64,.06)
  for off in (-1.95,1.95):H.ring('Hinge journal end',(x+off,9.55,1.67),.40,.24,.13,'steel','X')
  H.box('Hinge anchor leaf',(x,8.86,1.35),(3.65,1.20,.25),'blacksteel',.08)
 # Closed lid is authored locally then rotated about a single physical rear hinge.
 start=len(H.PARTS)
 H.rounded('Machined display lid',(0,-.2,2.13),(32.0,21.2,.62),'navy',.80,.105)
 H.rounded('Continuous lid perimeter gasket',(0,-.2,1.825),(31.60,20.85,.13),'rubber',.65,.025)
 H.rounded('Display inner bezel',(0,-.2,1.760),(31.35,20.6,.08),'keycap',.64,.020)
 H.rounded('Dark anti-reflective LCD',(0,-.18,1.710),(29.65,18.70,.028),'screen',.20,.008)
 H.cylinder('Webcam optical window',(0,-10.03,1.701),.13,.032,'blueglass',sides=48,edge=.005)
 H.cylinder('Webcam microphone bore',(.55,-10.03,1.700),.043,.02,'ink',sides=16,edge=0)
 H.box('Webcam privacy shutter guide',(-.48,-10.03,1.698),(.34,.15,.02),'blacksteel',.04)
 H.stamp('Lid inlaid maker mark','CS',(0,-.15,2.455),1.22,'silverfoil')
 H.stamp('Lid series marking','FIELDNOTE',(0,1.35,2.456),.31,'silverfoil')
 LID_OBJECTS=list(H.PARTS[start:]);pivot=Vector(LID_PIVOT)
 H.transform_since(start,Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-108),4,'X')@Matrix.Translation(-pivot))
 H.COLLISIONS=[((0,0,.88),(32.1,21.8,1.65))]
 # A lid collision slab uses the same authored hinge transform, rather than filling empty space.
 at=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-108),4,'X')@Matrix.Translation(-pivot)@Vector((0,-.2,2.08))
 H.COLLISIONS.append((tuple(at),(32.0,21.2,.72),('X',math.radians(-108))))
def player():
 body=H.rounded('Anodized personal player unibody',(0,0,5.65),(5.3,1.50,11.1),'navy',.50,.12)
 H.rounded('Rear polymer service plate',(0,.776,5.55),(4.96,.09,10.55),'plastic',.40,.025)
 H.rounded('Front glass gasket',(0,-.777,6.8),(4.82,.10,8.25),'rubber',.38,.035)
 H.rounded('Display glass sheet',(0,-.838,7.15),(4.60,.035,6.97),'screen',.28,.012)
 H.panel('Player printed idle display',(0,-.860,7.15),4.27,6.25,'PlayerScreen','-Y')
 for x,text in [(-1.45,'<'),(0,'II'),(1.45,'>')]:
  H.cylinder('Playback button '+text,(x,-.87,1.87),.40,.16,'blacksteel','Y',48,.03)
  H.stamp('Playback legend '+text,text,(x,-.971,1.88),.28,'white',rot=(math.pi/2,0,0))
 H.ring('Headphone jack rim',(-1.35,0,11.22),.26,.174,.17,'steel',sides=56)
 H.cylinder('Deep headphone socket',(-1.35,0,11.03),.17,.06,'ink',sides=40,edge=0)
 H.ring('Balanced audio rim',(-.35,0,11.22),.25,.17,.17,'gold',sides=56)
 H.cylinder('Balanced audio interior',(-.35,0,11.03),.17,.06,'ink',sides=40,edge=0)
 knurl('Volume encoder',(1.55,0,11.30),.54,.41,48,'Z','edge')
 H.cylinder('Encoder top insert',(1.55,0,11.52),.43,.035,'navy',sides=64,edge=.012)
 for x in (-2.10,2.10):
  for z in (.7,10.5):H.screw('Rear service fastener',(x,.84,z),.10,'Y')
 H.panel('Rear product information',(0,.833,5.58),3.75,3.75,'Player','Y')
 H.cut(body,(0,0,.14),(1.18,.58,.75),.15)
 socket_frame('USB-C connector',(0,0,.145),1.08,.46,.12,.045,'steel','Z',.16)
 H.box('USB-C tongue',(0,0,.285),(.68,.08,.045),'plastic',.02)
 for i in range(8):H.box('USB contact',(i*.073-.255,-.045,.28),(.035,.018,.08),'gold',.003)
 H.box('Memory card dust cover',(2.67,0,3.05),(.07,.80,2.00),'rubber',.05)
 for z in (7.1,8.05):H.rounded('Side navigation rocker',(2.68,0,z),(.12,.72,.65),'blacksteel',.11,.025)
 H.COLLISIONS=[((0,0,5.8),(5.5,1.95,11.6))]
def camera():
 body=H.rounded('Magnesium camera body',(0,0,3.40),(11.20,3.65,6.65),'blacksteel',.72,.14)
 H.rounded('Top satin aluminum plate',(0,0,6.75),(10.95,3.52,.38),'aluminum',.59,.06)
 H.rounded('Bottom service cover',(0,0,.19),(10.85,3.45,.26),'plastic',.52,.045)
 H.rounded('Textured hand grip',(-4.42,-1.75,3.45),(2.25,.75,5.82),'leather',.55,.17)
 H.rounded('Back thumb grip',(-4.45,1.89,4.50),(1.35,.23,3.25),'rubber',.30,.07)
 cx=.55;cz=3.50
 for name,outer,inner,y,depth,reg in [('Fixed bayonet seat',2.65,2.04,-1.91,.32,'edge'),('Rear telescopic barrel',2.44,1.99,-2.30,.63,'blacksteel'),('Middle telescopic barrel',2.22,1.83,-2.85,.54,'aluminum'),('Front focus barrel',2.04,1.67,-3.31,.43,'blacksteel'),('Lens front rim',1.94,1.59,-3.57,.17,'edge')]:
  H.ring(name,(cx,y,cz),outer,inner,depth,reg,'Y',96)
 for i in range(72):
  a=i*math.tau/72;H.cylinder('Focus ring flute',(cx+2.04*math.cos(a),-3.31,cz+2.04*math.sin(a)),.026,.29,'blacksteel','Y',8,.006)
 H.cylinder('Lens deep optical well',(cx,-2.52,cz),1.82,.04,'ink','Y',96,0)
 glass_lens('Multicoated convex front optical element',(cx,-3.39,cz),1.55,.18)
 for radius in (1.67,1.78):H.ring('Internal lens baffle',(cx,-3.45,cz),radius,radius-.045,.14,'blacksteel','Y',96)
 for i,(t,x) in enumerate([('CS OPTICS',cx),('24.8 ASPH',cx)]):
  H.stamp('Lens barrel engraving '+t,t,(x,-3.672,cz+(1.78 if i==0 else -1.78)),.17,'white',rot=(math.pi/2,0,0))
 # Recessed flash with actual ribbed diffuser, AF lamp and front plate fasteners.
 H.rounded('Flash recess',(-3.25,-1.845,5.93),(2.9,.10,.76),'ink',.12,.018)
 H.rounded('Flash diffuser',(-3.25,-1.915,5.93),(2.66,.045,.57),'ceramic',.08,.010)
 for i in range(15):H.box('Flash optical rib',(-4.43+i*.168,-1.951,5.93),(.027,.025,.50),'white',.006)
 H.ring('AF assist bezel',(4.10,-1.88,5.78),.25,.18,.09,'edge','Y',48)
 H.cylinder('AF assist glass',(4.10,-1.94,5.78),.17,.035,'blueglass','Y',48,.012)
 knurl('Mode selector',(3.58,.15,7.06),.86,.39,48,'Z','blacksteel')
 for i,t in enumerate(['P','A','S','M']):
  a=math.tau*i/4;H.stamp('Mode legend '+t,t,(3.58+.48*math.cos(a),.15+.48*math.sin(a),7.267),.20,'white')
 H.cylinder('Shutter button',(-3.9,0,7.04),.54,.30,'edge',sides=64,edge=.065)
 H.ring('Zoom rocker collar',(-3.9,0,6.97),.77,.53,.17,'blacksteel',sides=64)
 H.box('Zoom lever',(-4.63,-.15,7.00),(.55,.30,.18),'blacksteel',.06)
 H.cylinder('Power switch',(-2.30,.15,7.03),.26,.14,'blacksteel',sides=40)
 H.rounded('Rear LCD bezel',(-.95,1.88,3.65),(6.85,.18,4.85),'rubber',.28,.045)
 H.rounded('Rear display cover',(-.95,1.995,3.65),(6.41,.045,4.38),'screen',.16,.012)
 H.ring('Rear control wheel',(3.76,1.98,3.48),.83,.37,.13,'aluminum','Y',64)
 H.cylinder('Menu set button',(3.76,2.08,3.48),.35,.08,'blacksteel','Y',48)
 for x,z,t in [(3.76,5.22,'MENU'),(3.76,1.74,'DISP'),(2.5,5.95,'>')]:
  H.cylinder('Rear button '+t,(x,1.99,z),.26,.16,'blacksteel','Y',40,.02)
  H.stamp('Rear button legend '+t,t,(x,2.091,z),.13,'white',rot=(math.pi/2,0,math.pi))
 H.rounded('Battery door seam',(-2.95,.0,.047),(3.65,2.63,.04),'ink',.20,.008)
 H.rounded('Battery door',(-2.95,0,.018),(3.52,2.49,.025),'blacksteel',.18,.006)
 H.box('Battery sliding latch',(-3.97,.45,.002),(.74,.20,.08),'plastic',.04)
 H.ring('Tripod socket brass bushing',(1.7,0,.022),.42,.25,.12,'bronze',sides=64)
 H.cylinder('Tripod socket interior',(1.7,0,.09),.245,.025,'ink',sides=48,edge=0)
 H.panel('Camera underside serial plate',(3.75,0,.046),2.65,1.06,'Camera','-Z')
 for x in (-5.64,5.64):
  H.ring('Strap eyelet',(x,.15,5.76),.29,.16,.20,'steel','X',48)
 for x in (-4.8,4.8):
  for y in (-1.1,1.1):H.screw('Bottom chassis screw',(x,y,.015),.095)
 H.stamp('Front camera model','CS / C-7',(3.45,-1.86,1.25),.27,'white',rot=(math.pi/2,0,0))
 H.COLLISIONS=[((0,0,3.5),(11.3,4.2,7.1)),((cx,-2.75,cz),(5.2,2.1,5.2))]
BUILDERS={'Perfume':perfume,'Laptop':laptop,'MusicPlayer':player,'Camera':camera}
