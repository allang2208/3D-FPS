"""Build missing precision architecture and furniture; reuse installed art directly.
No render, simulation, validation or application launch. Source + FBX publication only.
"""
import sys,math,json,hashlib,random
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent.parent/'RefinementV3'))
from refinement_design import *
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
g.ROOM='Apartment'
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
placements=[];lights=[];notes=[];no_collision=set();glass_groups=set();world_meshes=set()
def B(k,c,s,m='Dark',col=False):g.box(k,c,s,m,collision=col)
def roundbox(k,c,s,m='Dark',r=.008,seg=4,col=False):
 bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.scale=s
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 # Segment long manufactured edges before rounding. A single metre-long bevel
 # triangle with a submillimetre width loses its tangent at the acute corner.
 # Coplanar interior divisions retain the silhouette and the specified radius.
 if max(s)>.70:
  bm=bmesh.new();bm.from_mesh(o.data)
  edges=[e for e in bm.edges if e.calc_length()>.70]
  bmesh.ops.subdivide_edges(bm,edges=edges,cuts=math.ceil(max(s)/.70)-1,use_grid_fill=True)
  bm.to_mesh(o.data);bm.free();o.data.update()
 mod=o.modifiers.new('Manufactured edge radius','BEVEL');mod.width=min(r,min(s)*.44);mod.segments=seg
 bpy.ops.object.modifier_apply(modifier=mod.name)
 vs=[o.matrix_world@v.co for v in o.data.vertices]
 g.poly(k,vs,[tuple(p.vertices) for p in o.data.polygons],m,
        smooth=[len(p.vertices)==4 and p.area<.02 for p in o.data.polygons])
 bpy.data.objects.remove(o,do_unlink=True)
 if col:g.box(None,c,s,collision=k)
def pipe(k,points,r=.008,m='Steel',sides=16):g.tube(k,points,r,m,sides)
def ring(k,c,axis,ro,ri,depth,m='Steel'):g.ring(k,c,axis,ro,ri,depth,m,48)
def text(k,string,c,size=.035,m='Warm',rotation=(90,0,0)):
 curve=bpy.data.curves.new('engraved type','FONT');curve.body=string;curve.size=size
 curve.extrude=.00065;curve.bevel_depth=.00015;curve.resolution_u=5
 o=bpy.data.objects.new('type',curve);bpy.context.collection.objects.link(o);o.location=c
 o.rotation_euler=tuple(math.radians(v) for v in rotation)
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH')
 vs=[o.matrix_world@v.co for v in o.data.vertices]
 g.poly(k,vs,[tuple(p.vertices) for p in o.data.polygons],m)
 bpy.data.objects.remove(o,do_unlink=True)
def place(label,key,p,yaw=0,scale=1,collision=True,room='',override=None):
 placements.append(dict(label=label,key=key,p=list(p),yaw=yaw,scale=scale,
                        collision=collision,room=room,override=override or {}))
def world(k,col=True):
 world_meshes.add(k)
 if not col:no_collision.add(k)
def light(label,p,w,d,power=1100,color=(1,.83,.63),radius=500,shadow=True,yaw=0):
 lights.append(dict(label=label,p=p,w=w,d=d,power=power,color=color,radius=radius,shadow=shadow,yaw=yaw))

# Accurate shell: no aggregate convex collision spanning doorways.
B('Foundation',(10,6.875,-.18),(20.30,14.05,.30),'Grout',True);world('Foundation')
B('BalconySlab',(9.55,-1.75,-.18),(9.35,3.5,.30),'Grout',True);world('BalconySlab')
B('EntryLanding',(12.4,15.10,-.18),(3.4,3.0,.30),'Grout',True);world('EntryLanding')
# Continuous flat collision top is separate from visual plank joints.
for k,c,s in [('FloorCollision',(10,6.875,-.015),(20,13.75,.03)),
              ('BalconyCollision',(9.55,-1.75,-.015),(9.15,3.5,.03)),
              ('LandingCollision',(12.4,15.10,-.015),(3.4,3,.03))]:
 B(k,c,s,'Grout',True);world(k)

for room,(x0,y0,x1,y1) in ROOMS.items():
 k='Floor_'+room;world(k,False)
 wood=room in ('Master','Living','Bed2','Bed3')
 step_x,step_y=(.20,1.50) if wood else (.80,.80)
 nx=math.ceil((x1-x0)/step_x);dx=(x1-x0)/nx
 for ix in range(nx):
  x=x0+ix*dx;start=y0-(.50 if ix%3==1 else 1. if ix%3==2 else 0)
  while start<y1:
   a=max(y0,start);b=min(y1,start+step_y)
   if b-a>.008:B(k,(x+dx/2,(a+b)/2,.006),(dx-.0025,b-a-.0025,.012),'Oak' if wood else 'Stone' if room=='Balcony' else 'Floor')
   start+=step_y
 if room!='Balcony':
  k='Ceiling_'+room;world(k)
  B(k,((x0+x1)/2,(y0+y1)/2,HEIGHT+.09),(x1-x0+.12,y1-y0+.12,.18),'Ceiling',True)
  # Perimeter reveal and dropped acoustic rafts share the ceiling underside datum.
  trim='CeilingTrim_'+room;world(trim,False)
  for x in (x0+.05,x1-.05):B(trim,(x,(y0+y1)/2,HEIGHT-.035),(.055,y1-y0-.12,.07),'Dark')
  for y in (y0+.05,y1-.05):B(trim,((x0+x1)/2,y,HEIGHT-.035),(x1-x0-.12,.055,.07),'Dark')

def wall(k,axis,const,start,end,thick=.15,gaps=(),finish='Wall'):
 world(k)
 def part(a,b,z0,z1):
  if b-a<.001 or z1-z0<.001:return
  c=[(a+b)/2,const,(z0+z1)/2];s=[b-a,thick,z1-z0]
  if axis=='Y':c[0],c[1]=c[1],c[0];s[0],s[1]=s[1],s[0]
  B(k,c,s,finish,True)
  # Low plinth and high shadow reveal stay on each actual solid span.
  if z0==0:
   for sign in (-1,1):
    for z,h,offset,mat in ((.065,.13,.009,'Dark'),(HEIGHT-.24,.025,.006,'Teal')):
     cc=c.copy();ss=s.copy();cc[2]=z;ss[2]=h
     normal=1 if axis=='X' else 0;cc[normal]+=sign*(thick/2+offset/2);ss[normal]=offset
     B(k,cc,ss,mat)
   # Modular vertical butt joints, inset cover strips at >1m spans.
   n=max(1,math.ceil((b-a)/1.15))
   for i in range(1,n):
    q=a+(b-a)*i/n
    for sign in (-1,1):
     cc=([q,const+sign*(thick/2+.002),1.70] if axis=='X' else [const+sign*(thick/2+.002),q,1.70])
     ss=([.006,.004,2.9] if axis=='X' else [.004,.006,2.9]);B(k,cc,ss,'Grout')
 last=start
 for a,b,h in sorted(gaps):
  part(last,a,0,HEIGHT);part(a,b,h,HEIGHT);last=b
 part(last,end,0,HEIGHT)

def oldwall(k,axis,c,a,b,th=.12,gaps=(),finish='Wall'):
 wall(k,axis,c*1.25,a*1.25,b*1.25,th*1.25,[(x*1.25,y*1.25,z*1.25) for x,y,z in gaps],finish)
oldwall('Wall_West','Y',0,0,11,.24)
# Window aperture in east wall, sill and lintel separate.
oldwall('Wall_East','Y',16,0,11,.24,[(6.8,9.6,2.62)])
B('Wall_East',(20,10.25,.2625),(.30,3.5,.525),'Wall',True)
oldwall('Wall_Back','X',11,0,16,.24,[(9.4,10.44,2.18)])
oldwall('Wall_Master','Y',3.9,0,5.4)
oldwall('Wall_EastPartition','Y',11.34,0,11,.12,[(4.1,5,2.08),(7.58,8.48,2.08)])
oldwall('Wall_CorridorSouth','X',5.46,0,11.34,.12,[(1.52,2.42,2.08),(6.60,9.60,2.42)])
oldwall('Wall_Bedrooms','X',5.46,11.34,16)
oldwall('Wall_CorridorNorth','X',6.78,0,11.34,.12,[(1.1,2.2,2.42),(3.48,4.58,2.42),(5.3,7.9,2.42),(9.4,10.44,2.42)])
oldwall('Wall_Bath2','X',8.14,0,2.72,.12,[(1.14,2.10,2.06)])
oldwall('Wall_Bath1','X',8.14,2.84,4.68,.12,[(3.22,4.18,2.06)])
oldwall('Wall_BathDivider','Y',2.78,6.78,11)
oldwall('Wall_Service','Y',4.74,6.78,11)
oldwall('Wall_Kitchen','Y',8.7,6.84,11)
wall('Landing_West','Y',10.7,13.75,16.6,.15)
wall('Landing_East','Y',14.1,13.75,16.6,.15)
wall('Landing_End','X',16.6,10.7,14.1,.15,finish='Teal')
B('EntryLanding',(12.4,15.175,.006),(3.4,2.85,.012),'Floor')
B('EntryLanding',(12.4,15.175,HEIGHT+.06),(3.4,2.85,.12),'Ceiling',True)
B('EntryLanding',(12.4,15.175,HEIGHT-.08),(1.8,.15,.06),'Dark')
B('EntryLanding',(12.4,15.175,HEIGHT-.113),(1.74,.10,.008),'Warm')
light('Landing',[12.4,15.175,HEIGHT-.12],174,10,900,radius=330)

# Facade pier spacing and openings are inherited exactly; frame system is new.
world('Facade');world('WindowFrames');world('WindowGlass',False);glass_groups.add('WindowGlass')
for a,b in [(0,.62),(3.36,4.02),(11.24,11.98),(15.56,16)]:
 B('Facade',((a+b)*.625,0,HEIGHT/2),((b-a)*1.25,.28,HEIGHT),'Teal',True)
for a,b in [(0,7),(8.1,16)]:B('Facade',((a+b)*.625,0,.10),((b-a)*1.25,.28,.20),'Dark',True)
B('Facade',(10,0,3.55625),(20,.28,.2625),'Teal',True)
def glazedspan(a,b,z0=.20,z1=3.425,y=0):
 n=math.ceil((b-a)/1.45);dx=(b-a)/n
 for i in range(n+1):
  x=a+i*dx
  roundbox('WindowFrames',(x,y,(z0+z1)/2),(.065,.16,z1-z0),'Dark',.004,col=True)
  B('WindowFrames',(x,y-.083,(z0+z1)/2),(.028,.006,z1-z0),'Steel')
 for z in (z0,z1):B('WindowFrames',((a+b)/2,y,z),(b-a,.17,.055),'Dark',True)
 for i in range(n):
  x=a+(i+.5)*dx
  B('WindowGlass',(x,y,(z0+z1)/2),(dx-.073,.014,z1-z0-.055),'Glass')
  # Independent closed pane collision, no hull covering neighboring opening.
  B('WindowPaneCollision',(x,y,(z0+z1)/2),(dx-.073,.026,z1-z0-.055),'Grout',True)
  for z in (z0+.032,z1-.032):B('WindowFrames',(x,y+.012,z),(dx-.07,.025,.012),'Rubber')
for a,b in [(.775,4.2),(5.025,8.75),(10.125,14.05),(14.975,19.45)]:glazedspan(a,b)
glazedspan(8.75,10.125,2.975,3.425)
world('WindowPaneCollision');no_collision.add('WindowFrames') # pane colliders and solid piers suffice
# Side window sits in the existing east bedroom opening.
for y in (8.5,9.67,10.83,12.):B('WindowFrames',(20,y,1.90),(.16,.06,2.75),'Dark')
for z in (.54,3.27):B('WindowFrames',(20,10.25,z),(.16,3.5,.06),'Dark')
for y in (9.085,10.25,11.415):
 B('WindowGlass',(20,y,1.90),(.014,1.10,2.67),'Glass')
 B('WindowPaneCollision',(20,y,1.90),(.028,1.10,2.67),'Grout',True)

# Recessed passage surrounds finish open portals without narrowing the walking route.
world('OpenPortalTrim',False)
for y,a,b,h in [(6.825,8.25,12,3.025),(8.475,6.625,9.875,3.025),
                 (8.475,11.75,13.05,3.025),(8.475,1.375,2.75,3.025),
                 (8.475,4.35,5.725,3.025)]:
 for x in (a-.02,b+.02):B('OpenPortalTrim',(x,y,h/2),(.04,.19,h),'Dark')
 B('OpenPortalTrim',((a+b)/2,y,h+.02),(b-a+.08,.19,.04),'Dark')
 B('OpenPortalTrim',((a+b)/2,y-.101,h+.025),(b-a-.05,.008,.012),'Cyan')

# Balcony has a human-height rail, independent from privacy screens and a real sill.
world('BalconyPrivacy');world('BalconyRail',False);world('BalconyRailGlass',False);glass_groups.add('BalconyRailGlass')
for x in (4.975,14.125):
 B('BalconyPrivacy',(x,-1.775,1.375),(.20,3.55,2.75),'Teal',True)
 for y in [-3.3+i*.15 for i in range(21)]:B('BalconyPrivacy',(x+.105,-1.775+(y+1.775),1.40),(.018,.045,2.25),'Dark')
for x in [5.10+i*(8.9/7) for i in range(8)]:
 roundbox('BalconyRail',(x,-3.43,.54),(.05,.06,1.08),'Steel',.007)
 B('BalconyRail',(x,-3.43,.015),(.15,.14,.03),'Dark')
pipe('BalconyRail',[(5.03,-3.43,1.10),(14.07,-3.43,1.10)],.027,'Steel',24)
for i in range(7):B('BalconyRailGlass',(5.10+(i+.5)*8.9/7,-3.43,.56),(8.9/7-.065,.018,.94),'Glass')
B('RailCollision',(9.55,-3.43,.55),(9.1,.08,1.10),'Grout',True);world('RailCollision')
for x in (4.975,14.125):B('BalconyRail',(x,-1.74,2.76),(.22,3.52,.025),'Steel')

# Independent real-sized furniture, authored only where the project has no suitable item.
def cabinet(k,w=1.8,d=.48,h=.72,doors=3):
 roundbox(k,(0,0,h/2+.08),(w,d,h-.12),'Oak',.009,col=True)
 B(k,(0,-d/2-.003,h/2+.08),(w-.045,.014,h-.18),'Dark')
 for i in range(doors):
  x=-w/2+(i+.5)*w/doors
  roundbox(k,(x,-d/2-.022,h/2+.06),(w/doors-.012,.032,h-.21),'Teal',.004)
  B(k,(x,-d/2-.043,h-.08),(w/doors-.06,.012,.018),'Brass')
 roundbox(k,(0,0,h),(w+.025,d+.025,.034),'Stone',.009)
 for x in (-w/2+.09,w/2-.09):
  for y in (-d/2+.07,d/2-.07):g.cylinder(k,(x,y,0),(x,y,.18),.018,'Dark',24)
cabinet('MediaConsole',2.9,.45,.58,5)
cabinet('EntryCabinet',1.8,.38,.95,3)
cabinet('Nightstand',.48,.42,.48,1)
cabinet('ServiceCabinet',1.50,.46,1.05,3)

def wardrobe():
 k='Wardrobe';w=2.4;d=.62;h=2.65
 roundbox(k,(0,0,h/2),(w,d,h),'Oak',.012,col=True)
 B(k,(0,-.317,h/2),(w-.07,.015,h-.08),'Dark')
 for i in range(4):
  x=-.9+i*.6
  roundbox(k,(x,-.34,h/2),(.586,.03,h-.08),'Teal' if i%2 else 'Oak',.006)
  pipe(k,[(x+.21,-.367,.92),(x+.21,-.397,.94),(x+.21,-.397,1.45),(x+.21,-.367,1.47)],.008,'Brass')
 B(k,(0,-.365,h-.05),(2.30,.015,.018),'Warm')
wardrobe()

def loop(cx,cy,z,w,d,r=.06):
 pts=[]
 for x,y,a in [(cx+w/2-r,cy+d/2-r,0),(cx-w/2+r,cy+d/2-r,90),
               (cx-w/2+r,cy-d/2+r,180),(cx+w/2-r,cy-d/2+r,270)]:
  for i in range(12):t=math.radians(a+i*90/11);pts.append((x+r*math.cos(t),y+r*math.sin(t),z))
 return pts+[pts[0]]
def pillow(k,c,w=.74,d=.48):
 # Closed, pinched perimeter with an inflated crown and restrained cloth creases.
 n=30;vs=[];fs=[]
 for side in (-1,1):
  for j in range(n+1):
   v=-1+2*j/n
   for i in range(n+1):
    u=-1+2*i/n;bulge=max(0,(1-u*u)*(1-v*v))
    x=u*w*.5*(1-.08*abs(v)**8);y=v*d*.5*(1-.08*abs(u)**8)
    z=side*(.012+.092*bulge**.57)+.007*math.sin(u*24+v*7)*abs(v)**5*(1-u*u)
    vs.append((c[0]+x,c[1]+y,c[2]+z))
 count=(n+1)**2
 for layer in range(2):
  for j in range(n):
   for i in range(n):
    a=layer*count+j*(n+1)+i;f=(a,a+1,a+n+2,a+n+1);fs.append(f if layer else tuple(reversed(f)))
 edge=list(range(n+1))+[j*(n+1)+n for j in range(1,n+1)]+[n*(n+1)+i for i in range(n-1,-1,-1)]+[j*(n+1) for j in range(n-1,0,-1)]
 for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,b,b+count,a+count))
 g.poly(k,vs,fs,'Linen',smooth=True)
 pipe(k,[vs[i] for i in edge]+[vs[edge[0]]],.0022,'Linen',8)
def bed(k,w=1.8):
 roundbox(k,(0,0,.24),(w+.14,2.22,.28),'Oak',.025,col=True)
 roundbox(k,(0,0,.095),(w-.18,1.90,.19),'Dark',.025)
 roundbox(k,(0,.01,.49),(w,2.05,.25),'Linen',.065,7,col=True)
 for z in (.395,.585):pipe(k,loop(0,.01,z,w-.025,2.025),.003,'Linen',8)
 roundbox(k,(0,1.18,.91),(w+.50,.10,1.42),'Oak',.022,col=True)
 for x in (-w*.25,w*.25):roundbox(k,(x,1.116,1.00),(w*.48,.07,.74),'Fabric',.035,6)
 for x in (-w*.25,w*.25):pillow(k,(x,.73,.69),w*.43,.47)
 # Duvet drapes over both long sides and the foot; edge return gives real thickness.
 nx=64;ny=60;vs=[];fs=[];width=w+.18
 for j in range(ny+1):
  y=-1.16+j*1.67/ny
  for i in range(nx+1):
   x=-width/2+i*width/nx
   sx=max(0,(abs(x)-(w/2-.11))/.20);sy=max(0,(-y-.90)/.26)
   z=.654-.23*min(1,sx)**1.4-.21*min(1,sy)**1.4
   z+=.012*math.sin(x*14+y*7)*math.exp(-((y+.15)/.9)**2)+.008*math.sin(y*28+x*5)*min(1,sx+.10)
   z+=.035*math.exp(-((y-.40)/.08)**2)
   vs.append((x,y,z))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
 start=len(vs);vs.extend((vs[i][0],vs[i][1],vs[i][2]-.025) for i in boundary)
 for j,a in enumerate(boundary):b=boundary[(j+1)%len(boundary)];fs.append((a,start+j,start+(j+1)%len(boundary),b))
 g.poly(k,vs,fs,'Fabric',smooth=True);pipe(k,[vs[i] for i in boundary]+[vs[boundary[0]]],.003,'Linen',8)
 for x in (-w/2-.13,w/2+.13):
  pipe(k,[(x,1.10,1.33),(x,1.00,1.33),(x,.94,1.27)],.012,'Brass')
  g.lathe(k,(x,.94,1.27),(0,0,-1),[(0,.025),(.05,.05),(.055,.05)],'Dark',40)
  g.cylinder(k,(x,.94,1.213),(x,.94,1.216),.042,'Warm',40)
bed('BedKing',1.80);bed('BedQueen',1.50)

def desk():
 k='WritingDesk';roundbox(k,(0,0,.76),(1.65,.68,.045),'Oak',.015,col=True)
 for x in (-.72,.72):
  for y in (-.23,.23):g.cylinder(k,(x,y,.015),(x,y,.74),.022,'Dark',32)
  pipe(k,[(x,-.24,.30),(x,.24,.30)],.012,'Steel')
 roundbox(k,(.51,.02,.63),(.43,.54,.20),'Teal',.01)
 B(k,(.51,-.257,.65),(.32,.015,.015),'Brass')
 # Monitor, stand, keyboard and thin desk mat are supported by the tabletop.
 roundbox(k,(0,.18,.798),(.29,.21,.020),'Dark',.008)
 B(k,(0,.23,.95),(.045,.055,.29),'Steel')
 roundbox(k,(0,.22,1.17),(.64,.035,.37),'Dark',.012)
 B(k,(0,.200,1.17),(.609,.005,.341),'Screen')
 roundbox(k,(0,-.16,.79),(.73,.32,.004),'Rubber',.014)
 roundbox(k,(-.04,-.19,.805),(.43,.14,.020),'Dark',.006)
 for i in range(14):
  for j in range(4):roundbox(k,(-.238+i*.029,-.235+j*.031,.819),(.024,.025,.006),'Teal',.002,2)
 roundbox(k,(.27,-.18,.813),(.057,.10,.035),'Dark',.018,5)
 pipe(k,[(0,.245,1.0),(0,.29,.83),(.25,.29,.785),(.64,.29,.78),(.72,.25,.62)],.003,'Rubber',8)
desk()

def kitchen():
 k='KitchenRun';w=3.60;d=.65;h=.92
 # Hollow carcasses and recessed toe kick, with separate doors and appliance face.
 B(k,(0,.05,.09),(w-.10,.50,.18),'Dark',True)
 for x in (-1.78,-1.2,-.6,0,.6,1.2,1.78):B(k,(x,0,.52),(.025,d,.75),'Oak',True)
 for z in (.18,.875):B(k,(0,0,z),(w,d,.025),'Oak',True)
 B(k,(0,.312,.53),(w,.025,.72),'Oak',True)
 for i in range(6):
  x=-1.5+i*.6
  if i==4:
   roundbox(k,(x,-.335,.52),(.574,.045,.65),'Steel',.009)
   roundbox(k,(x,-.363,.46),(.49,.012,.39),'Dark',.015)
   B(k,(x,-.372,.46),(.43,.006,.31),'Screen')
   pipe(k,[(x-.21,-.38,.71),(x-.21,-.41,.71),(x+.21,-.41,.71),(x+.21,-.38,.71)],.010,'Steel')
   for xx in (x-.17,x+.17):g.cylinder(k,(xx,-.374,.78),(xx,-.395,.78),.025,'Dark',40)
  else:
   for j in range(2 if i<2 else 1):
    hh=.335 if i<2 else .69;z=.35+j*.35 if i<2 else .52
    roundbox(k,(x,-.34,z),(.584,.033,hh),'Teal',.005)
    B(k,(x,-.363,z+hh/2-.038),(.50,.015,.018),'Brass')
 # Worktop with a genuine open sink aperture, not a dark painted rectangle.
 for x,wid in [(-1.65,.30),(.55,2.50)]:roundbox(k,(x,0,h),(wid,.70,.04),'Stone',.008)
 for y in (-.30,.30):roundbox(k,(-1.1,y,h),(.80,.10,.04),'Stone',.006)
 B(k,(-1.1,0,.738),(.69,.47,.022),'Steel')
 for x in (-1.445,-.755):B(k,(x,0,.825),(.018,.49,.18),'Steel')
 for y in (-.245,.245):B(k,(-1.1,y,.825),(.71,.018,.18),'Steel')
 g.cylinder(k,(-1.1,0,.750),(-1.1,0,.754),.033,'Dark',48)
 for x in (-1.47,-.73):B(k,(x,0,.928),(.022,.53,.012),'Steel')
 for y in (-.265,.265):B(k,(-1.1,y,.928),(.762,.022,.012),'Steel')
 pipe(k,[(-1.1,.27,.94),(-1.1,.27,1.20),(-1.1,.24,1.26),(-1.1,.10,1.26),(-1.1,.055,1.22)],.013,'Steel',24)
 g.cylinder(k,(-.94,.27,.94),(-.94,.27,1.00),.023,'Steel',32)
 # Induction glass and fine concentric printed rings.
 roundbox(k,(.9,-.02,.948),(.57,.52,.015),'Dark',.012)
 for x in (.76,1.04):
  for y in (-.15,.12):ring(k,(x,y,.956),(0,0,1),.093,.092,.001,'Steel')
 B(k,(0,.362,1.19),(3.60,.025,.51),'Stone')
 # Floating upper cabinetry leaves a usable 59cm counter clearance.
 for i in range(6):
  x=-1.5+i*.6
  if i==4:
   roundbox(k,(x,.13,1.75),(.59,.44,.08),'Steel',.01)
   B(k,(x,.23,2.18),(.29,.24,.82),'Dark')
   for j in range(11):B(k,(x-.22+j*.044,-.085,1.72),(.018,.26,.005),'Dark')
  else:
   roundbox(k,(x,.19,2.13),(.59,.38,.94),'Oak',.008,col=True)
   roundbox(k,(x,-.016,2.13),(.58,.032,.925),'Teal',.005)
   B(k,(x,-.036,1.72),(.49,.012,.016),'Brass')
  B(k,(x,.04,1.647),(.52,.022,.012),'Warm')
kitchen()

def planter():
 k='Planter';g.lathe(k,(0,0,0),(0,0,1),[(0,.20),(.03,.22),(.40,.29),(.44,.29),(.44,.27),(.38,.265),(.04,.19)],'Ceramic',80,True)
 g.cylinder(k,(0,0,.385),(0,0,.395),.263,'Soil',64)
 ring(k,(0,0,.43),(0,0,1),.293,.286,.022,'Brass')
planter()
def showertray():
 k='ShowerTray';roundbox(k,(0,0,.035),(1.20,1.20,.07),'Stone',.018,col=True)
 for x in (-.575,.575):B(k,(x,0,.079),(.05,1.2,.022),'Ceramic')
 B(k,(0,.575,.079),(1.1,.05,.022),'Ceramic')
 for i in range(18):B(k,(-.34+i*.04,.43,.073),(.023,.075,.004),'Steel')
showertray()
def laundry():
 k='Washer';roundbox(k,(0,0,.43),(.61,.61,.86),'Ceramic',.025,col=True)
 roundbox(k,(0,-.313,.72),(.56,.022,.15),'Teal',.008)
 ring(k,(0,-.327,.38),(0,1,0),.222,.175,.044,'Steel')
 g.lathe(k,(0,-.35,.38),(0,-1,0),[(0,.176),(.012,.17),(.035,.14)],'Dark',72)
 ring(k,(0,-.392,.38),(0,1,0),.154,.146,.009,'Rubber')
 g.cylinder(k,(-.20,-.33,.73),(-.20,-.353,.73),.033,'Steel',48)
 B(k,(.12,-.329,.74),(.18,.008,.057),'Screen')
 text(k,'ECO / 40',(0,-.336,.731),.013,'Cyan')
 B(k,(-.15,-.323,.10),(.15,.009,.055),'Teal')
 for i in range(10):B(k,(-.24+i*.052,.308,.24),(.020,.004,.22),'Dark')
laundry()

# Small supported accessories are merged within a reusable tray or shelf, not loose actors.
k='CoffeeTray';roundbox(k,(0,0,.012),(.47,.31,.024),'Oak',.018)
for x in (-.12,.10):
 g.lathe(k,(x,0,.024),(0,0,1),[(0,.032),(.005,.037),(.079,.042),(.084,.04),(.084,.034),(.014,.029)],'Ceramic',48)
 g.torus(k,(x+.052,0,.072),(0,1,0),.026,.006,'Ceramic',32,10)
 B(k,(x,.10,.027),(.09,.05,.005),'Paper')
k='Magazines'
for i in range(3):
 B(k,(i*.007,i*.009,.007+i*.014),(.26,.34,.012),'Paper')
 B(k,(i*.007,i*.009,.014+i*.014),(.264,.344,.002),'Teal' if i%2 else 'Dark')
text(k,'NEON / BAY',(-.103,-.12,.045),.025,'Paper',rotation=(0,0,0))

# Native sliding door art, with bounded thickness and a clear split at the centre.
for d in DOORS:
 w=d['width'];h=d['height'];k='Door_'+d['name']+'_Frame'
 for side in (-1,1):
  roundbox(k,(0,side*(w/2+.035),h/2),(.20,.07,h+.07),'Dark',.008,col=True)
  B(k,(-.106,side*(w/2+.035),h/2),(.012,.018,h-.05),'Steel')
 roundbox(k,(0,0,h+.05),(.22,w+.18,.10),'Dark',.009,col=True)
 B(k,(-.116,0,h+.045),(.009,w-.08,.018),'Cyan' if d['name']=='Balcony' else 'Warm')
 # Author in native local axes after export, Y is reflected but symmetric geometry stays correct.
 k='Door_'+d['name']+'_Leaf'
 if d['name']=='Balcony':
  B(k,(0,0,h/2),(.014,w-.07,h-.15),'Glass')
  for side in (-1,1):roundbox(k,(0,side*(w/2-.0175),h/2),(.062,.035,h),'Dark',.005)
  for z in (.0375,h-.0375):roundbox(k,(0,0,z),(.062,w-.07,.075),'Dark',.005)
  g.box(None,(0,0,h/2),(.062,w,h),collision=k);glass_groups.add(k)
 else:
  roundbox(k,(0,0,h/2),(.062,w,h),'Teal',.008,col=True)
  B(k,(-.037,0,h*.55),(.012,w-.08,h-.32),'Oak' if d['name'] in ('Master','Bed2','Bed3') else 'Dark')
 for side in (-1,1):
  B(k,(-.047,side*(w/2-.025),h/2),(.008,.017,h-.05),'Steel')
 # Native actor uses this prototype twice at Y=.5; one handle per prototype
 # produces one correctly placed handle on each actual sliding leaf.
 pipe(k,[(-.05,0,1.03),(-.080,0,1.05),(-.08,0,1.38),(-.05,0,1.40)],.009,'Steel')
 for z in (.18,h-.18):B(k,(-.048,0,z),(.008,w-.11,.012),'Brass')

# Fixture geometry, shared anchors for lights and diffusers; no light floating through a ceiling.
for room,(x0,y0,x1,y1) in ROOMS.items():
 if room=='Balcony':continue
 k='Lighting_'+room;world(k,False)
 cx=(x0+x1)/2;cy=(y0+y1)/2
 width=min(2.4,(x1-x0)-.40)
 roundbox(k,(cx,cy,HEIGHT-.11),(width,.16,.09),'Dark',.012)
 B(k,(cx,cy,HEIGHT-.159),(width-.06,.115,.012),'Warm')
 power=4500 if room=='Living' else 2800 if room=='Kitchen' else 2200 if room in ('Master','Bed2','Bed3') else 1200 if room.startswith('Bath') else 850
 light(room,[cx,cy,HEIGHT-.17],(width-.06)*100,11.5,power,radius=650 if room=='Living' else 420)
 # Two rows of recessed ceiling acoustic panels, with narrow seams and real frame edges.
 if room in ('Living','Master','Bed2','Bed3'):
  for sign in (-1,1):
   for i in range(4):B(k,(cx+(i-1.5)*.49,cy+sign*.56,HEIGHT-.044),(.47,.54,.08),'Teal')
 # Service vent; backing is dark and every fin has thickness.
 ventx=x1-.42;venty=y1-.30
 B(k,(ventx,venty,HEIGHT-.014),(.56,.23,.028),'Dark')
 for i in range(12):B(k,(ventx-.25+i*.045,venty,HEIGHT-.034),(.017,.20,.018),'Steel')

# Furniture assembly placements. All transforms are keyed and maintainable.
place('NearTower','NearTower',(0,0,0),scale=1.25,collision=False,room='Exterior')
place('Living_Sofa','Sofa',(7.35,3.35,0),90,room='Living',override={'Fabric':'Fabric','Seam':'Fabric'})
place('Living_CoffeeTable','CoffeeTable',(9.13,3.35,0),90,room='Living')
place('Living_Console','MediaConsole',(13.72,2.50,0),-90,room='Living')
place('Living_TV','TV',(14.014,2.50,.91),-90,.80,False,'Living')
place('Living_Tray','CoffeeTray',(9.13,3.16,.500),20,collision=False,room='Living')
place('Living_Magazines','Magazines',(9.13,3.76,.50),-8,collision=False,room='Living')
place('Living_ReadingShelf','Bookcase',(5.18,4.55,0),90,room='Living')
place('Living_ReadingChair','Chair',(5.85,2.0,0),-25,room='Living')
# Rug lies fully below the sitting group; bound border is actual geometry.
k='LivingRug';roundbox(k,(8.5,3.35,.019),(4.35,3.35,.014),'Carpet',.007);world(k,False)
pipe(k,loop(8.5,3.35,.028,4.30,3.30,.05),.003,'Fabric',8)
for label,p,key,yaw in [('Master_Bed',(2.75,4.45,0),'BedKing',0),('Bed2_Bed',(17.25,4.30,0),'BedQueen',0),('Bed3_Bed',(17.9,12.23,0),'BedQueen',0)]:
 room=label.split('_')[0];place(label,key,p,yaw,room=room)
 w=1.8 if key=='BedKing' else 1.5
 for side in (-1,1):place(room+'_Nightstand_'+str(side),'Nightstand',(p[0]+side*(w/2+.35),p[1]+.83,0),room=room)
place('Master_Wardrobe','Wardrobe',(.50,2.54,0),90,room='Master')
place('Bed2_Wardrobe','Wardrobe',(19.49,4.73,0),-90,room='Bed2')
place('Bed3_Wardrobe','Wardrobe',(15.76,7.30,0),180,room='Bed3')
place('Master_Desk','WritingDesk',(3.94,1.35,0),-90,room='Master')
place('Master_Chair','OfficeChair',(3.02,1.35,0),90,room='Master')
place('Bed2_Desk','WritingDesk',(16.60,.90,0),180,room='Bed2')
place('Bed2_Chair','OfficeChair',(16.60,1.83,0),0,room='Bed2')
place('Bed3_Desk','WritingDesk',(19.42,9.25,0),-90,room='Bed3')
place('Bed3_Chair','OfficeChair',(18.48,9.25,0),90,room='Bed3')
place('Bed3_Bookcase','Bookcase',(14.55,12.52,0),90,room='Bed3')
place('Kitchen_Run','KitchenRun',(8.9,13.12,0),room='Kitchen')
place('Kitchen_Dining','DiningTable',(8.35,10.28,0),room='Kitchen')
for i,(x,y,yaw) in enumerate([(7.85,9.47,180),(8.85,9.47,180),(7.85,11.09,0),(8.85,11.09,0)]):place('Dining_Chair'+str(i),'Chair',(x,y,0),yaw,room='Kitchen')
for part in ('Lower','Upper'):
 place('Fridge_'+part+'Body','Fridge'+part+'Body',(6.52,13.10,0),room='Kitchen')
 place('Fridge_'+part+'Door','Fridge'+part+'Door',(6.165,12.717,0),room='Kitchen')
place('Kitchen_Coffee','CoffeeMachine',(10.37,13.05,.94),scale=.75,collision=False,room='Kitchen')
place('Kitchen_Kettle','Kettle',(8.78,13.08,.94),collision=False,room='Kitchen')
place('Entry_Storage','EntryCabinet',(13.80,11.65,0),-90,room='Foyer')
place('Laundry_Washer','Washer',(.59,9.12,0),90,room='Laundry')
place('Laundry_Hamper','LaundryBasket',(1.40,9.14,0),room='Laundry')
place('Service_Storage','ServiceCabinet',(4.6,9.35,0),room='Service')
for room,x0,x1 in [('Bath2',.15,3.40),('Bath1',3.55,5.85)]:
 # Fixtures mounted to the inland wall; entry-facing working floor stays clear.
 sinkx=x0+.53;toiletx=x1-.48;showerx=x1-.68
 place(room+'_Basin','Basin',(sinkx,13.322,0),room=room)
 place(room+'_Mirror','Mirror',(sinkx,13.492,1.20),collision=False,room=room)
 place(room+'_Toilet','Toilet',(toiletx,11.20,0),-90,room=room)
 place(room+'_Tray','ShowerTray',(showerx,12.94,0),room=room)
 place(room+'_Shower','Shower',(showerx,13.56,.07),collision=False,room=room)
 place(room+'_Towels','TowelRack',(x0+.10,11.32,1.20),90,collision=False,room=room)
 # Open shower entry, single fixed splash screen, no enclosing collision box.
 k='ShowerScreen_'+room;world(k,False);glass_groups.add(k)
 B(k,(showerx-.60,13.15,1.17),(.012,.79,2.18),'Glass')
 k='ShowerTrim_'+room;world(k)
 for y in (12.75,13.55):B(k,(showerx-.60,y,1.17),(.025,.025,2.20),'Steel',True)
 B(k,(showerx-.60,13.15,2.27),(.025,.80,.025),'Steel')
 g.box(None,(showerx-.60,13.15,1.17),(.022,.79,2.18),collision=k)
 # Wet-area cladding, with actual grout gaps and supported accessory mounting faces.
 k='WetCladding_'+room;world(k,False)
 n=math.ceil((x1-x0)/.60);dx=(x1-x0)/n
 for ix in range(n):
  for iz in range(5):B(k,(x0+(ix+.5)*dx,13.585,.30+iz*.60),(dx-.003,.026,.597),'Ceramic')
 for x in (x0+.015,x1-.015):
  for iy in range(6):
   for iz in range(5):B(k,(x,10.25+(iy+.5)*(3.35/6),.30+iz*.60),(.026,3.35/6-.003,.597),'Ceramic')
 for z in (.065,3.02):B(k,((x0+x1)/2,13.565,z),(x1-x0-.025,.016,.025),'Brass')

for i,(p,sc) in enumerate([((5.63,.82,0),.58),((13.35,5.85,0),.56),((1.0,6.20,0),.45),((19.20,.72,0),.52),((5.55,-2.65,0),.65),((13.4,-2.65,0),.60)]):
 room='Balcony' if p[1]<0 else 'Living'
 place('Planter'+str(i),'Planter',p,room=room)
 place('Foliage'+str(i),'Plant' if i%2==0 else 'Plant2',(p[0],p[1],.39),scale=sc,collision=False,room=room)
place('Balcony_Table','CoffeeTable',(7.1,-2.32,0),room='Balcony')
for i,(x,y,yaw) in enumerate([(6.42,-1.26,0),(7.92,-1.26,-15)]):place('Balcony_Chair'+str(i),'Chair',(x,y,0),yaw,room='Balcony')

# Residential cyberpunk details: supported consoles, door identifiers, sockets, acoustic battens.
world('ResidentialDetails',False)
for x in [5.28+i*.075 for i in range(13)]:B('ResidentialDetails',(x,6.735,1.60),(.038,.045,2.75),'Oak')
roundbox('ResidentialDetails',(13.995,12.50,1.55),(.048,.46,.70),'Dark',.012)
B('ResidentialDetails',(13.966,12.50,1.60),(.008,.38,.48),'Screen')
for room,(x0,y0,x1,y1) in ROOMS.items():
 if room in ('Balcony','Corridor'):continue
 x=x0+.05;y=y1-.40
 B('ResidentialDetails',(x,y,.34),(.025,.16,.10),'Dark')
 for yy in (y-.042,y+.042):
  B('ResidentialDetails',(x+.014,yy,.34),(.003,.016,.038),'Steel')
 # Switch lives on solid wall, away from the sliding panels.
for name,x,y,word in [('Foyer',11.01,12.5,'NIGHTFALL / 09'),('Master',.46,6.735,'01 / PRIVATE'),
                     ('Kitchen',7.0,8.57,'KITCHEN / GALLEY')]:
 roundbox('ResidentialDetails',(x,y,2.50),(1.0,.028,.19),'Dark',.008)
 text('ResidentialDetails',word,(x-.44,y-.017,2.46),.072,'Warm')
for x,y in [(8.78,13.20),(10.37,13.24)]:
 pipe('ResidentialDetails',[(x,y,.963),(x+.05,13.38,.946),(x+.15,13.43,.946),
                             (x+.15,13.43,1.13),(x+.15,13.45,1.15)],.0035,'Rubber',12)
 roundbox('ResidentialDetails',(x+.15,13.453,1.15),(.10,.030,.11),'Dark',.004)
 roundbox('ResidentialDetails',(x+.15,13.429,1.15),(.039,.021,.044),'Rubber',.004)

# Flush thresholds tie room floor finishes through each wall reveal.
world('Thresholds',False)
for d in DOORS:
 s=(d['width']+.09,.55,.012) if d['yaw']==90 else (.55,d['width']+.09,.012)
 B('Thresholds',(d['p'][0],d['p'][1],.006),s,'Steel')
for y,a,b in [(6.825,8.25,12.),(8.475,6.625,9.875),(8.475,11.75,13.05),
               (8.475,1.375,2.75),(8.475,4.35,5.725)]:
 B('Thresholds',((a+b)/2,y,.006),(b-a,.25,.012),'Stone')

# Pleated linen side drapes, full height, with a real hem and rail carriers.
world('WindowDrapes',False);world('CurtainTracks',False)
for a,b in [(.82,1.25),(3.70,4.12),(5.08,5.57),(13.48,13.98),(15.03,15.48),(18.95,19.39)]:
 nx=48;nz=44;vs=[];fs=[]
 for j in range(nz+1):
  t=j/nz;z=.16+t*3.32
  for i in range(nx+1):
   u=i/nx;x=a+(b-a)*u+.008*math.sin(t*8+u*6)*(1-t)
   y=.32+.064*math.cos(u*math.tau*5)*(1-.24*t)+.008*math.sin(t*12+u*15)*(1-t)
   vs.append((x,y,z+.009*math.sin(u*math.tau*5)*(1-t)))
 for j in range(nz):
  for i in range(nx):
   q=j*(nx+1)+i;fs.append((q,q+nx+1,q+nx+2,q+1))
 # Give cloth a thin reverse skin; texture sampling stays physically sized.
 offset=len(vs);vs.extend((x,y+.002,z) for x,y,z in vs[:])
 fs+= [tuple(offset+v for v in reversed(f)) for f in fs[:]]
 # Continuous cloth coordinates follow the weave across the folds. Dominant-axis
 # box projection would reverse U on alternating pleats and cancel seam tangents.
 cloth_uv=[[(float((v%offset)%(nx+1))/nx*(b-a)/.25,
             float((v%offset)//(nx+1))/nz*3.32/.25) for v in face] for face in fs]
 g.poly('WindowDrapes',vs,fs,'Linen',uv=cloth_uv,smooth=True)
 pipe('WindowDrapes',vs[:nx+1],.004,'Linen',8)
 for i in range(6):ring('CurtainTracks',(a+(b-a)*i/5,.32,3.505),(1,0,0),.018,.013,.012,'Steel')
 B('CurtainTracks',((a+b)/2,.32,3.54),(b-a+.06,.035,.04),'Dark')
for a,b in [(.78,4.20),(5.03,14.05),(14.98,19.45)]:B('CurtainTracks',((a+b)/2,.32,3.57),(b-a,.07,.04),'Dark')
world('PracticalLights',False)
# Dining pendant uses the table's anchor; shade and emitter share the same origin.
for x in (7.85,8.85):
 pipe('PracticalLights',[(x,10.28,HEIGHT),(x,10.28,2.42)],.004,'Dark',12)
 g.lathe('PracticalLights',(x,10.28,2.28),(0,0,1),[(0,.16),(.015,.17),(.14,.05)],'Teal',64)
 g.cylinder('PracticalLights',(x,10.28,2.274),(x,10.28,2.279),.152,'Warm',48)
 light('Dining_'+str(x),[x,10.28,2.268],24,24,200,radius=160,shadow=False)
B('PracticalLights',(9.4375,-.19,3.43),(1.65,.18,.08),'Dark')
B('PracticalLights',(9.4375,-.19,3.386),(1.55,.11,.008),'Cyan')
light('Balcony',[9.4375,-.19,3.378],155,11,600,(.48,.72,1),400,True)

# Apply this revision at the assembly boundary, before exports: separated cabinet
# bodies/moving fronts, revised room uses, supported accessories and exact reveals.
from refinement_parts import apply_refinement
refinement=apply_refinement(globals())
from refinement_v3_parts import apply_v3
apply_v3(globals(),refinement)
from cabinet_upgrade import apply_v4
apply_v4(globals(),refinement)

# Finish material placeholders in .blend are replaced by exact shared UE paths on import.
materials={}
preview={'Oak':(.25,.135,.06),'Steel':(.31,.34,.34),'Dark':(.025,.030,.032),'Fabric':(.055,.075,.078),
         'Linen':(.60,.55,.44),'Carpet':(.09,.10,.10),'Glass':(.20,.31,.33),'Stone':(.26,.27,.25),'Floor':(.28,.29,.27)}
for key,path in MATERIALS.items():
 m=bpy.data.materials.new('AP_'+key);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 color=FINISHES[key][0] if key in FINISHES else preview.get(key,(.25,.27,.26))
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.6
 if key in FINISHES and FINISHES[key][3]:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=FINISHES[key][3]
 if key=='Glass':p.inputs['Alpha'].default_value=.10;p.inputs['Transmission Weight'].default_value=.85
 materials[key]=m
records=[]
previous_rows={r['key']:r for r in json.loads((ROOT.parent/'RefinementV3/assembly.json').read_text('utf8'))['meshes']}
for (_,kind),data in g.G.items():
 name='SM_AP_'+kind;mesh=bpy.data.meshes.new(name);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
 order=list(dict.fromkeys(data['m']))
 for key in order:mesh.materials.append(materials[key])
 uv=mesh.uv_layers.new(name='UVMap')
 for face,mat,coords,sm in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
  face.material_index=order.index(mat);face.use_smooth=sm
  axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))]
  scale=.25 if mat in ('Fabric','Linen','Carpet') else 1.0
  for j,li in enumerate(face.loop_indices):
   p=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=coords[j] if coords else (p[axes[0]]/scale,p[axes[1]]/scale)
 # Manufactured pieces already carry their own designed radii. Do not add a
 # second microscopic bevel to every wall, invisible collider and floor slab.
 normal=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');normal.keep_sharp=True
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 bpy.ops.object.modifier_apply(modifier=normal.name)
 triangulate=o.modifiers.new('Export triangles','TRIANGULATE');triangulate.keep_custom_normals=True
 bpy.ops.object.modifier_apply(modifier=triangulate.name)
 mesh=o.data
 # Fresh bevel faces must have area in UV space as well as geometry. Reproject
 # final triangles at physical scale; inherited collapsed bevel UVs cannot bake tangents.
 uv=mesh.uv_layers.active
 for face in (mesh.polygons if kind!='WindowDrapes' else []):
  if order[face.material_index] in ('OfficeUI','WorkoutUI'):continue
  axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))]
  mat=order[face.material_index];scale=.25 if mat in ('Fabric','Linen','Carpet') else 1.
  for li in face.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/scale,p[axes[1]]/scale)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
 hulls=[]
 for i,(vs,fs) in enumerate(g.C.get(('Apartment',kind),[])):
  cm=bpy.data.meshes.new('UCX_'+name+'_'+str(i));cm.from_pydata(vs,[],fs);cm.update()
  co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);hulls.append(co)
 fbx=OUT/(name+'.fbx')
 reuse_old=kind in previous_rows and kind not in v3_changed
 if not reuse_old:bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                          bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
 triangles=sum(len(p.vertices)-2 for p in mesh.polygons)
 records.append(dict(key=kind,name=name,asset=BASE+'/Meshes/'+name,fbx=str(fbx),
                     materials={'AP_'+k:MATERIALS[k] for k in order},triangles=triangles,
                     collision=bool(hulls) and kind not in no_collision,
                     hulls=len(hulls),nanite=kind not in glass_groups and not kind.startswith('Door_') and triangles>15000,
                     hidden=kind in ('FloorCollision','BalconyCollision','LandingCollision','WindowPaneCollision','RailCollision') or kind in v3_hidden))
 if reuse_old:
  records[-1]=dict(previous_rows[kind],reused_revision='RefinementV3')
 for co in hulls:bpy.data.objects.remove(co,do_unlink=True)
 o.select_set(False)
 if kind in world_meshes:place(kind,kind,(0,0,0),collision=kind not in no_collision,room='Architecture')
# Editable complete assembly: object prototypes are instantiated at their design transforms.
protos={r['key']:bpy.data.objects[r['name']] for r in records}
for o in protos.values():o.hide_render=True;o.hide_set(True)
for p in placements:
 if p['key'] not in protos:continue
 src=protos[p['key']];o=src.copy();o.name=p['label'];bpy.context.collection.objects.link(o)
 o.location=p['p'];o.rotation_euler[2]=math.radians(p['yaw']);o.scale=(p['scale'],)*3;o.hide_render=False;o.hide_set(False)
 o['UE_asset']=BASE+'/Meshes/SM_AP_'+p['key']
for p in placements:
 if p['key'] in REUSE:
  o=bpy.data.objects.new(p['label'],None);bpy.context.collection.objects.link(o);o.empty_display_type='CUBE';o.empty_display_size=.15
  o.location=p['p'];o.rotation_euler[2]=math.radians(p['yaw']);o['UE_asset']=REUSE[p['key']];o['shared_asset_instance']=True
for c in refinement['containers']:
 root=bpy.data.objects.new('Container_'+c['label'],None);bpy.context.collection.objects.link(root)
 root.location=c['p'];root.rotation_euler[2]=math.radians(c['yaw']);root['ContainerId']=c['id']
 for key,loc in ((c['body'],(0,0,0)),(c['front'],c['hinge'])):
  if key not in protos:continue
  ob=protos[key].copy();bpy.context.collection.objects.link(ob);ob.name=c['label']+'_'+key
  ob.parent=root;ob.location=loc;ob.hide_set(False);ob.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'CyberpunkApartment_Rebuild.blend'))
manifest=dict(revision='20261022',map=MAP,base=BASE,rooms=ROOMS,ceiling_underside_m=HEIGHT,
              source_layout_scale=1.50,instance_scale=SCENE_SCALE,furniture_scale_policy='physical sizes; independent assets',
              meshes=records,placements=placements,doors=DOORS,lights=lights,reuse=REUSE,
              material_reuse=MATERIALS,geometry_toolkit=str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts/geometry.py'),
              spawn=dict(p=[12.40,12.55,1.00],yaw_ue=90,capsule_radius_cm=42,capsule_half_height_cm=96),
              tests_run=False,rendered=False)
manifest.update(refinement)
(ROOT/'assembly.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print('APARTMENT_AUTHORED',len(records),'meshes',len(placements),'placements',flush=True)
