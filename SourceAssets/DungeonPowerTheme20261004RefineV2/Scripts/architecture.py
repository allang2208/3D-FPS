"""Three purpose-built room shells. New architecture only; existing props reused.
Plans/sections deliberately differ. Ports, walkable slab and UCX are co-authored.
"""
import math
from mathutils import Vector

def architecture(g,cfg,atlas):
 def sign(c,w,h,key,n=(0,-1,0)):g.plate(c,w,h,key,n,atlas)
 def marked_lane(x0,x1,y,width=.05):g.box('Markings',((x0+x1)/2,y,.008),(x1-x0,width,.008),'Yellow')
 def rim_joint(a,b,z=1.48):g.beam('Trim',(*a,z),(*b,z),.035,.045,'Paint')
 def i_beam(a,b,w=.28,h=.44):
  a,b=Vector(a),Vector(b);n,u,v=g.basis(b-a)
  g.beam('RoofFrame',a,b,.055,h,'Paint')
  for s in (-1,1):g.beam('RoofFrame',a+v*s*h/2,b+v*s*h/2,w,.038,'Paint')
 def cable_hangers(x0,x1,y,z,top,step=3.0):
  g.tray((x0,y),(x1,y),z)
  n=max(1,math.ceil((x1-x0)/step))
  for i in range(n+1):
   x=x0+(x1-x0)*i/n
   for dy in (-.29,.29):g.cylinder('Cablework',(x,y+dy,z-.07),(x,y+dy,top),.012,'Steel',10)
   g.beam('Cablework',(x,y-.34,z-.075),(x,y+.34,z-.075),.04,.04,'Steel')
 def handrail_plate(a,b,height=1.08):g.rail(a,b,height=height)
 # 01: a T-shaped low distribution gallery with a genuinely usable service nook.
 g.ROOM='SwitchgearGallery';g.pavement(-9,-8,9,8);g.pavement(-3,8,3,11)
 g.wall((-9,-8),(9,-8),4.8);g.wall((9,-8),(9,8),4.8,True);g.wall((-9,8),(-9,-8),4.8,True)
 g.wall((9,8),(3,8),4.8);g.wall((-3,8),(-9,8),4.8)
 g.box('Structure',(0,8,4.1),(6,.30,1.4),'Concrete',collision=True)
 for a,b in [((-3,8),(-3,11)),((-3,11),(3,11)),((3,11),(3,8))]:g.wall(a,b,3.6)
 g.box('Roof',(0,0,4.95),(18.3,16.3,.30),'Concrete',collision=True);g.box('Roof',(0,9.5,3.75),(6.3,3.3,.3),'Concrete',collision=True)
 for x in (-7.5,-3.75,0,3.75,7.5):
  i_beam((x,-7.7,4.35),(x,7.7,4.35),.24,.34)
  for y in (-7.68,7.68):
   if y>0 and abs(x)<3.2:continue
   g.box('Structure',(x,y,2.1),(.28,.32,4.2),'Concrete',collision=True)
   g.box('Trim',(x,y,.25),(.42,.44,.50),'Concrete')
 # Flush drain/cable covers, continuous concrete beneath; no unsafe fake pit.
 for y in (-3.20,3.20):
  g.box('Trim',(0,y,.004),(14.8,.64,.012),'Dark')
  for yy in (-.33,.33):g.box('Trim',(0,y+yy,.024),(14.85,.045,.05),'Steel')
  for i in range(148):g.box('Trim',(-7.4+(i+.5)*.10,y,.027),(.022,.62,.044),'Deck')
  marked_lane(-7.7,7.7,y+(.48 if y>0 else -.48))
 cable_hangers(-8.5,8.5,-5.7,3.45,4.69);cable_hangers(-8.5,8.5,5.7,3.45,4.69)
 # Wall-mounted feeder conduits stop at registered cabinet anchors, clear of aisle.
 for x in (-6,-2,2,6):
  for y in (-5.7,5.7):
   for dx in (-.12,0,.12):g.rounded_pipe('Cablework',[(x+dx,y,3.43),(x+dx,y,2.10),(x+dx,y+(-.10 if y<0 else .10),1.89)],.028,'Rubber',10)
 sign((0,-7.81,3.35),3.8,.90,'Switchgear',(0,1,0))
 sign((8.79,0,3.40),2.2,.62,'Exit',(-1,0,0));sign((-8.79,2.70,2.10),1.45,.60,'Danger',(1,0,0))
 sign((0,10.80,2.62),2.2,.63,'Route')
 # 02: double-height shallow vault, lower through route and accessible high gallery.
 g.ROOM='GeneratorHall';g.pavement(-13,-11,13,11)
 for y in (-11,11):g.wall((-13,y),(13,y),6.8)
 for x in (-13,13):g.wall((x,-11),(x,11),6.8,True)
 segments=48
 profile=[(11*math.cos(math.pi*i/segments),6.8+2.2*math.sin(math.pi*i/segments)) for i in range(segments+1)]
 # End lunette masonry occupies the actual curved roof profile, never a square top.
 for x in (-13,13):
  vs=[(xx,y,z) for xx in (x-.15,x+.15) for y,z in profile];n=len(profile)
  fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
  g.poly('Structure',vs,fs,'Concrete');g.hull('Structure',vs,fs)
 # Closed barrel shell is thickness-bearing, with matched convex UCX strips.
 for i in range(segments):
  a=math.pi*i/segments;b=math.pi*(i+1)/segments
  cross=[(11*math.cos(a),6.8+2.2*math.sin(a)),(11*math.cos(b),6.8+2.2*math.sin(b)),(11.28*math.cos(b),6.8+2.48*math.sin(b)),(11.28*math.cos(a),6.8+2.48*math.sin(a))]
  vs=[(x,y,z) for x in (-13.15,13.15) for y,z in cross];g.poly('Roof',vs,g.FACES,'Concrete');g.hull('Roof',vs,g.FACES)
 for x in (-10.5,-5.25,0,5.25,10.5):
  for y in (-10.53,10.53):g.i_column(x,y,6.75)
  pts=[(x,10.70*math.cos(math.pi*i/24),6.65+2.08*math.sin(math.pi*i/24)) for i in range(25)]
  for a,b in zip(pts,pts[1:]):i_beam(a,b,.28,.34)
 # Structural full-length gallery. Open underside is 2.19 m; stairs 15x16 cm.
 g.box('Structure',(0,9.125,2.28),(25.3,3.15,.24),'Concrete',collision=True)
 for x in (-10.65,10.65):g.stairs(x,2.15,1.8,15,.16,.36)
 for x in (-11.7,-7.8,-3.9,0,3.9,7.8,11.7):
  g.box('Structure',(x,9.65,1.05),(.18,.24,2.1),'Paint',collision=True)
  i_beam((x,7.58,2.07),(x,10.66,2.07),.18,.22)
 # Leave exact 1.84m stair mouths free; no rail crossing the top tread.
 for a,b in [(-12.55,-11.57),(-9.73,9.73),(11.57,12.55)]:g.rail((a,7.57,2.4),(b,7.57,2.4))
 for x in (-12.55,12.55):g.rail((x,7.57,2.4),(x,10.63,2.4))
 # Actual grating infill on upper gallery, on top of a continuous walkable deck.
 for x in range(-12,13):
  g.box('Trim',(x,9.05,2.407),(.035,2.84,.014),'Deck')
 for y in (7.76,8.12,8.48,8.84,9.20,9.56,9.92,10.28):g.box('Trim',(0,y,2.407),(24.8,.025,.014),'Deck')
 for y in (-4.25,4.25):
  g.box('Structure',(0,y,.14),(9.3,3.9,.28),'Concrete',collision=True)
  # Foot pads are part of the new generator; plinth remains in architecture.
  for yy in (y-2.10,y+2.10):marked_lane(-5.0,5.0,yy,.075)
  for xx in (-5.0,5.0):g.box('Markings',(xx,y,.008),(.075,4.27,.008),'Yellow')
 for y in (-8.50,6.80):cable_hangers(-12.4,12.4,y,5.70,6.74)
 # Connected cooling mains enter walls; future pipe assets are not duplicated.
 for y in (-10.10,10.10):
  g.rounded_pipe('Pipework',[(-12.8,y,4.70),(12.8,y,4.70)],.16,'Enamel',28)
  for x in (-9,-3,3,9):
   g.flange('Hardware',(x,y,4.70),(1,0,0),.16,8)
   g.beam('Hardware',(x,y,4.50),(x,y+(-.70 if y<0 else .70),4.50),.045,.07,'Steel')
 sign((0,-10.80,4.35),4.4,1.05,'Generators',(0,1,0))
 sign((-7,-10.80,2.4),1.8,.65,'Warning',(0,1,0));sign((7,-10.80,2.4),1.8,.65,'Danger',(0,1,0))
 sign((0,7.52,3.22),3.0,.68,'Gallery');sign((12.80,0,3.45),2.2,.62,'Exit',(-1,0,0))
 # 03: station-scale circular hall, annular gallery and enclosed control room.
 from round_hall import build_round_hall
 build_round_hall(g,cfg,atlas)
 # Connection geometry is independent, zero stretch of authored room shells.
 for link in cfg['connectors']:
  # Slab and finish continue beneath the recessed lining's full footprint.
  # Only jamb faces retain ±1.500 ownership; the floor has no side voids.
  g.ROOM=link['id'];g.pavement(-3,-1.86,3,1.86,.75)
  # Door jamb clear faces own y=±1.500. Corridor lining is recessed 60mm
  # and starts 200mm beyond the room centre plane, so no common face remains.
  for y in (-1.71,1.71):g.wall((-2.80,y),(2.80,y),3.2,thickness=.30)
  # Short stepped backing connects lining to the frame behind its visible face.
  # Inner backing is 40mm outside the jamb face; it seals the 10mm butt gap.
  for x in (-2.815,2.815):
   for y in (-1.685,1.685):g.box('Structure',(x,y,1.60),(.11,.29,3.20),'Concrete',collision=True)
  g.box('Roof',(0,0,3.35),(6,3.72,.30),'Concrete',collision=True)
  for x in (-2,0,2):
   g.box('Trim',(x,0,3.09),(.07,3.16,.07),'Steel')
   for y in (-1.555,1.555):g.box('Trim',(x,y,1.55),(.07,.07,3.05),'Steel')
  g.tray((-3,1.15),(3,1.15),2.96,.30)

 # Hangers terminate on the real room ceiling; all lamp housings are reused.
 for section in cfg['rooms']+cfg['connectors']:
  g.ROOM=section['id']
  for part in section.get('reused_parts',[]):
   if part.get('source_asset_id')!='SM_Staff_LampFixture':continue
   x,y,z=part['position_m']
   if section['id']=='GeneratorHall':ceiling=6.8+2.2*math.sqrt(max(0,1-(y/11)**2))
   elif section['id']=='SwitchgearGallery':ceiling=3.6 if y>8 else 4.8
   elif section['id']=='AccumulatorControl':ceiling=part.get('ceiling_m',section['dimensions_m'][2])
   else:ceiling=3.2
   for dx in (-.48,.48):
    if ceiling>z+.045:g.cylinder('Hangers',(x+dx,y,z+.045),(x+dx,y,ceiling-.015),.012,'Steel',10)
    g.box('Hangers',(x+dx,y,ceiling-.017),(.09,.12,.018),'Steel')
