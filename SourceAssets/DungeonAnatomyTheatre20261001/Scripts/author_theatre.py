"""D-shaped anatomy theatre: four seating tiers and four usable stair routes."""
from pathlib import Path
SCRIPT_DIR=Path(__file__).resolve().parent
exec(compile((SCRIPT_DIR/'geometry.py').read_text('utf-8'),str(SCRIPT_DIR/'geometry.py'),'exec'))
OUT=Path(globals().get('EXPORT_OUT',OUT));OUT.mkdir(parents=True,exist_ok=True)
detail.setup(globals());ROOM['height_m']=CFG['hall']['height'];outline=CFG['hall']['outline']
for key in ('Wood','Ceramic','Chalkboard','LampGlass'):
 MAPPING[key]=CFG['ue_base']+'/Materials/M_Theatre_'+key
 MATS[key]=bpy.data.materials.new('RS_'+key)
MAPPING['Wood']=CFG['seating']['wood_material']
wood_board_index=0
def wood_board(kind,c,size,yaw):
 # Scanned workbench wood uses lengthwise grain, per-board offsets and neutral vertex tint.
 global wood_board_index
 box(kind,c,size,'Wood',yaw);g=G[kind];start=len(g['v'])-8
 co,si=math.cos(yaw),math.sin(yaw)
 points=[]
 for v in g['v'][start:]:
  dx,dy=v[0]-c[0],v[1]-c[1]
  points.append((dx*co+dy*si,-dx*si+dy*co,v[2]-c[2]))
 offset=((wood_board_index*.193)%1,(wood_board_index*.231)%1)
 for fi in range(6):
  face=g['f'][-6+fi];coords=[]
  for vi in face:
   p=points[vi-start]
   # Each face has a non-degenerate local projection; end caps expose cross grain.
   u0,v0=(p[1]/.27,p[2]/.08) if fi in (3,5) else (p[0]/1.72,(p[1] if fi in (0,1) else p[2])/.62)
   coords.append((u0+offset[0],v0+offset[1]))
  g['uv'][-6+fi]=coords
 wood_board_index+=1
def prism(kind,points,z0,z1,mat):
 n=len(points);vs=[(x,y,z) for z in (z0,z1) for x,y in points]
 poly(kind,vs,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],mat)
def sector(kind,inner,outer,a,b,z0,z1,mat):
 count=max(1,math.ceil((b-a)/3))
 for i in range(count):
  t0=math.radians(a+(b-a)*i/count);t1=math.radians(a+(b-a)*(i+1)/count)
  prism(kind,[(inner*math.cos(t0),-2+inner*math.sin(t0)),(outer*math.cos(t0),-2+outer*math.sin(t0)),
    (outer*math.cos(t1),-2+outer*math.sin(t1)),(inner*math.cos(t1),-2+inner*math.sin(t1))],z0,z1,mat)
def clip(points,axis,value,greater):
 if not points:return []
 out=[];a=points[-1];da=(a[axis]-value)*(1 if greater else -1)
 for b in points:
  db=(b[axis]-value)*(1 if greater else -1)
  if (da>=0)!=(db>=0):
   t=da/(da-db);out.append([a[k]+(b[k]-a[k])*t for k in range(2)])
  if db>=0:out.append(b)
  a,da=b,db
 return out
def arc_points(radius,a,b,z):
 n=max(2,math.ceil((b-a)/3))
 return [(radius*math.cos(math.radians(a+(b-a)*i/n)),-2+radius*math.sin(math.radians(a+(b-a)*i/n)),z) for i in range(n+1)]
prism('Floors',outline,-.32,-.025,'Concrete')
for ix in range(24):
 for iy in range(21):
  x0=-14+ix*28/24+.004;x1=-14+(ix+1)*28/24-.004;y0=-12+iy*24/21+.004;y1=-12+(iy+1)*24/21-.004
  p=outline
  for axis,v,above in ((0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)):p=clip(p,axis,v,above)
  if len(p)>2:prism('Paving',p,-.025,0,'Ceramic')
for i,a in enumerate(outline):
 b=outline[(i+1)%len(outline)];opening=[]
 if abs(a[0])==14 and abs(b[0])==14 and abs(a[1]-b[1])>5:
  opening=[dict(center=abs(-10-a[1]),width=3.,height=2.8)]
 wall_segment(a,b,8,opening,tiles=True)
prism('Roof',outline,8,8.32,'Concrete')
# The inner stair edge leaves over 3 m between the two handrails.
blocks=[(20,43),(77,103),(137,160)]
for row in range(4):
 r0=5.7+row*1.2;r1=r0+1.2;top=(row+1)*.54
 for a,b in blocks:
  sector('Terraces',r0,r1,a,b,-.015,top-.025,'Concrete')
  sector('TerraceFinish',r0+.006,r1-.006,a+.04,b-.04,top-.025,top,'Ceramic')
  detail.tube('Nosing',arc_points(r0+.025,a+.15,b-.15,top+.004),.012,'BareSteel',12)
  radius=r0+.65;num=max(2,int(math.radians(b-a)*radius/.82))
  for j in range(num):
   angle=math.radians(a+(b-a)*(j+.5)/num);rad=Vector((math.cos(angle),math.sin(angle),0));tan=Vector((-rad.y,rad.x,0))
   centre=Vector((radius*rad.x,-2+radius*rad.y,top));yaw=angle+math.pi/2
   # Bolted steel chair frame, three separate seat slats, inclined back slats and writing ledge.
   for side in (-1,1):
    p=centre+tan*side*.27
    box('SeatFrames',p+Vector((0,0,.015)),(.13,.16,.03),'BareSteel',yaw)
    beam('SeatFrames',p+rad*.12+Vector((0,0,.04)),p+rad*.12+Vector((0,0,.76)),.035,.035,'PaintedSteel')
    beam('SeatFrames',p-rad*.16+Vector((0,0,.04)),p-rad*.16+Vector((0,0,.44)),.035,.035,'PaintedSteel')
    beam('SeatFrames',p-rad*.2+Vector((0,0,.42)),p+rad*.23+Vector((0,0,.42)),.035,.035,'PaintedSteel')
    for offset in (-.044,.044):detail.fastener(p+tan*offset+Vector((0,0,.034)),(0,0,1),.007,'SeatHardware')
   for offset in (-.14,0,.14):wood_board('SeatWood',centre+rad*offset+Vector((0,0,.46)),(.68,.125,.045),yaw)
   for z in (.62,.76):
    wood_board('SeatWood',centre+rad*(.23+(z-.62)*.15)+Vector((0,0,z)),(.68,.045,.12),yaw)
   if (row*11+j)%13!=4:
    wood_board('WritingLedges',centre-rad*.29+Vector((0,0,.77)),(.7,.19,.034),yaw)
    for side in (-1,1):beam('SeatFrames',centre+tan*side*.27-rad*.16+Vector((0,0,.35)),centre+tan*side*.27-rad*.29+Vector((0,0,.75)),.025,.025,'BareSteel')
for a,b in CFG['radial_stairs']['angle_intervals_deg']:
 for step in range(12):
  r0=5.7+step*.4;top=(step+1)*.18
  sector('RadialStairs',r0,r0+.4,a,b,-.012,top,'Concrete')
  detail.tube('Nosing',arc_points(r0+.025,a+.15,b-.15,top+.005),.012,'BareSteel',12)
 # Handrail feet stand on individual tread planes, inside the usable stair wedge.
 for edge in (a+1.0,b-1.0):
  t=math.radians(edge);ps=[]
  for step in (0,2,4,6,8,10,11):
   r=5.7+(step+.5)*.4;z=(step+1)*.18;p=Vector((r*math.cos(t),-2+r*math.sin(t),z))
   box('Railings',p+Vector((0,0,.012)),(.13,.13,.024),'BareSteel')
   detail.tube('Railings',[p+Vector((0,0,.024)),p+Vector((0,0,1.02))],.025,'PaintedSteel',12)
   ps.append(p+Vector((0,0,1.02)))
  detail.tube('Railings',ps,.028,'PaintedSteel',16)
# Continuous upper observation gallery, 3.22 m deep behind the seating.
sector('Gallery',10.5,13.72,20,160,0,2.16,'Concrete')
for a,b in ((0,20),(160,180)):sector('Gallery',9.3,13.72,a,b,0,2.16,'Concrete')
for sign in (-1,1):
 x=sign*11.35
 for step in range(12):
  top=(step+1)*.18;y=-7.4+(step+.5)*.45
  box('SideStairs',(x,y,(top-.03)/2),(4.,.45,top+.03),'Concrete')
  box('Nosing',(x,y-.45/2+.022,top+.005),(3.75,.036,.01),'BareSteel')
 for edge in (-1,1):
  px=x+edge*(2-.14);posts=[]
  for step in (0,2,4,6,8,10,11):
   p=Vector((px,-7.4+(step+.5)*.45,(step+1)*.18))
   box('Railings',p+Vector((0,0,.012)),(.15,.15,.024),'BareSteel')
   detail.tube('Railings',[p+Vector((0,0,.025)),p+Vector((0,0,1.04))],.028,'PaintedSteel',12)
   posts.append(p+Vector((0,0,1.04)))
  detail.tube('Railings',posts,.03,'PaintedSteel',16)
  detail.tube('Railings',[p-Vector((0,0,.5)) for p in posts],.022,'PaintedSteel',12)
for a,b in ((0,20),(160,180)):
 for z in (2.69,3.22):detail.tube('Railings',arc_points(9.3,a,b,z),.028,'PaintedSteel',16)
 for p in arc_points(9.3,a,b,2.16)[::3]:
  detail.tube('Railings',[p,(p[0],p[1],3.22)],.028,'PaintedSteel',12)
  box('Railings',(p[0],p[1],2.172),(.15,.15,.024),'BareSteel')
# Standard-level vestibules; retired sample caps are excluded from production authoring.
for sign in (-1,1):
 a,b=sorted((sign*14.,sign*16.));box('Floors',((a+b)/2,-10,-.15),(2.,4.,.3),'Concrete')
 wall_segment((a,-12),(b,-12),3.4,tiles=True);wall_segment((b,-8),(a,-8),3.4,tiles=True)
 wall_segment((sign*16,-12),(sign*16,-8),3.4,[dict(center=2,width=3.,height=2.8)],tiles=True)
 box('Roof',((a+b)/2,-10,3.54),(2.28,4.28,.28),'Concrete')
# Elevated roof ribs and perimeter service ring preserve sight lines across the arena.
for angle in (24,60,90,120,156):
 t=math.radians(angle);beam('RoofRibs',(0,-2,7.67),(13.55*math.cos(t),-2+13.55*math.sin(t),7.67),.22,.42,'Concrete')
detail.tube('Services',arc_points(13.6,0,180,6.6),.075,'PipeEnamel',24)
for x in (-10,-5,0,5,10):
 box('RoofRibs',(x,-7,7.75),(.22,9.9,.5),'Concrete')
for p in arc_points(13.6,0,180,6.6)[::8]:
 beam('Services',p,(p[0],p[1],7.94),.045,.045,'BareSteel')
# Main teaching table: formed rim, inset draining surface, pedestal and foot control.
cx,cy=0,-8.8
box('AutopsyTable',(cx,cy,.09),(1.8,.88,.18),'PaintedSteel')
box('AutopsyTable',(cx,cy,.49),(1.3,.64,.68),'PipeEnamel')
box('AutopsyTable',(cx,cy,.95),(2.5,.91,.12),'BareSteel')
box('AutopsyTable',(cx,cy,1.023),(2.40,.80,.026),'BareSteel')
for y in (-.455,.455):box('AutopsyTable',(cx,cy+y,1.06),(2.5,.032,.14),'BareSteel')
for x in (-1.24,1.24):box('AutopsyTable',(cx+x,cy,1.06),(.032,.91,.14),'BareSteel')
for y in (-.26,0,.26):beam('AutopsyTable',(cx-1.12,cy+y,1.041),(cx+1.10,cy+y,1.041),.012,.012,'BareSteel')
detail.ring((.97,cy,1.045),(0,0,1),.052,.032,.012,'BareSteel',32,'AutopsyTable')
detail.tube('AutopsyTable',[(.97,cy,.92),(.97,cy,.64),(.65,cy,.64)],.035,'BareSteel',20)
for x in (-.43,.43):box('AutopsyTable',(x,cy-.48,.14),(.27,.28,.065),'Rubber')
for side in (-1,1):
 detail.tube('AutopsyTable',[(-1.05,cy+side*.51,.88),(1.05,cy+side*.51,.88)],.018,'BareSteel',16)
 for x in (-.88,.88):beam('AutopsyTable',(x,cy+side*.43,.89),(x,cy+side*.51,.89),.025,.025,'BareSteel')
# Articulated surgical lamp has actual joints, a reflector housing, lenses and sterile handle.
detail.tube('SurgicalLight',[(0,cy,7.92),(0,cy,5.45)],.085,'PipeEnamel',32)
for p,q in [((0,cy,5.45),(.9,cy,5.45)),((.9,cy,5.45),(.9,cy,3.75)),((.9,cy,3.75),(0,cy,3.35))]:
 beam('SurgicalLight',p,q,.12,.095,'PipeEnamel');detail.tube('SurgicalLight',[(p[0],p[1]-.085,p[2]),(p[0],p[1]+.085,p[2])],.105,'BareSteel',32)
detail.tube('SurgicalLight',[(0,cy,3.14),(0,cy,3.37)],.55,'PipeEnamel',64)
detail.ring((0,cy,3.115),(0,0,1),.55,.48,.045,'BareSteel',64,'SurgicalLight')
for i in range(6):
 t=i*math.tau/6;x=.34*math.cos(t);y=cy+.34*math.sin(t)
 detail.ring((x,y,3.08),(0,0,1),.14,.115,.046,'BareSteel',32,'SurgicalLight')
 detail.tube('SurgicalLight',[(x,y,3.065),(x,y,3.075)],.113,'LampGlass',32)
detail.tube('SurgicalLight',[(0,cy,3.1),(0,cy,2.88)],.03,'Rubber',20)
detail.torus((0,cy,2.91),(0,0,1),.09,.014,'SurgicalLight','BareSteel')
# Front teaching board: all faces sit clear of the wall and their solid frames.
box('TeachingBoard',(0,-11.73,3.28),(6.4,.12,1.9),'BareSteel')
box('TeachingBoard',(0,-11.655,3.28),(6.15,.025,1.68),'Chalkboard')
box('TeachingBoard',(0,-11.50,2.39),(6.25,.32,.055),'BareSteel')
box('TeachingBoard',(0,-11.63,4.65),(6.2,.08,.48),'PipeEnamel')
def lettering(text,location,size):
 curve=bpy.data.curves.new('Teaching inscription','FONT');curve.body=text;curve.size=size;curve.align_x='CENTER';curve.extrude=.001
 obj=bpy.data.objects.new('Teaching inscription',curve);bpy.context.collection.objects.link(obj);obj.location=location;obj.rotation_euler=(math.pi/2,0,math.pi)
 bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.convert(target='MESH')
 mesh=obj.data;vs=[obj.matrix_world@v.co for v in mesh.vertices]
 poly('Lettering',vs,[tuple(p.vertices) for p in mesh.polygons],'BareSteel');bpy.data.objects.remove(obj,do_unlink=True)
lettering('ANATOMY THEATRE / AT-01',(0,-11.58,4.51),.24)
for light in CFG['lights']:
 if not light['fixture']:continue
 x,y,z=light['position'];ceiling=3.4 if abs(x)>14 else 8
 for offset in (-.28,.28):
  detail.tube('LampHangers',[(x+offset,y,z+.06),(x+offset,y,ceiling-.025)],.011,'BareSteel',12)
  box('LampHangers',(x+offset,y,ceiling-.018),(.10,.10,.028),'BareSteel')
EXPORT_BLEND_NAME=globals().get('EXPORT_BLEND_NAME','AbandonedAnatomyTheatre_Structure.blend')
exec(compile((SCRIPT_DIR/'export_geometry.py').read_text('utf-8'),str(SCRIPT_DIR/'export_geometry.py'),'exec'))
