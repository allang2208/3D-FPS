"""Faceted hall, sunken dispatch floor, four stairs, raised ring and empty equipment bays."""
from pathlib import Path
SCRIPT_DIR=Path(__file__).resolve().parent
exec(compile((SCRIPT_DIR/'geometry.py').read_text(encoding='utf-8'),str(SCRIPT_DIR/'geometry.py'),'exec'))
detail.setup(globals());ROOM['height_m']=6.1;outline=CFG['hall']['outline']
for key,path in [('Screen',CFG['ue_base']+'/Materials/M_DormantScreen'),('Panel',CFG['ue_base']+'/Materials/M_ArchivePanel')]:
 MAPPING[key]=path;MATS[key]=bpy.data.materials.new('RS_'+key)
 MATS[key].diffuse_color=(.013,.023,.027,1) if key=='Screen' else (.16,.19,.17,1)
def prism(kind,points,z0,z1,mat):
 n=len(points);vs=[(x,y,z) for z in (z0,z1) for x,y in points]
 fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 poly(kind,vs,fs,mat)
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
def clipped_rect(a,b,c,d):
 p=outline
 for axis,value,greater in ((0,a,True),(0,c,False),(1,b,True),(1,d,False)):p=clip(p,axis,value,greater)
 return p
def floor_patch(a,b,c,d,top):
 p=clipped_rect(a,b,c,d)
 if len(p)<3:return
 prism('Floors',p,top-.3,top-.025,'Concrete')
 nx=max(1,math.ceil((c-a)/1.2));ny=max(1,math.ceil((d-b)/1.2))
 for ix in range(nx):
  for iy in range(ny):
   x0=a+(c-a)*ix/nx+.003;y0=b+(d-b)*iy/ny+.003
   q=clipped_rect(x0,y0,a+(c-a)*(ix+1)/nx-.003,b+(d-b)*(iy+1)/ny-.003)
   if len(q)>=3:prism('Paving',q,top-.025,top,'Panel')
# Subdivide only to cut the four real stair wells out of the raised floor.
xs=[-12,-8.4,-6,-1.8,1.8,6,8.4,12];ys=[-12,-8.4,-6,-2,2,6,8.4,12]
for a,c in zip(xs,xs[1:]):
 for b,d in zip(ys,ys[1:]):
  x,y=(a+c)/2,(b+d)/2
  if abs(x)<6 and abs(y)<6:continue
  if 6<=abs(x)<8.4 and abs(y)<2:continue
  if 6<=abs(y)<8.4 and abs(x)<1.8:continue
  floor_patch(a,b,c,d,0)
floor_patch(-6,-6,6,6,-.6)
for axis,width in [(0,4.),(1,3.6)]:
 for sign in (-1,1):
  for i in range(4):
   t=sign*(8.4-(i+.5)*.6);top=-(i+1)*.15
   p=(t,0,(top-.85)/2) if axis==0 else (0,t,(top-.85)/2)
   size=(.6,width,top+.85) if axis==0 else (width,.6,top+.85)
   box('Stairs',p,size,'Concrete')
   nose=sign*(8.4-i*.6-.022)
   p=(nose,0,top+.004) if axis==0 else (0,nose,top+.004)
   box('Nosing',p,(.035,width-.06,.008) if axis==0 else (width-.06,.035,.008),'Yellow')
# Retaining faces are below the rail level, leaving the centre open to every side.
for x in (-6,6):
 for a,b in [(-6,-2),(2,6)]:box('PitCoping',(x,(a+b)/2,-.32),(.16,b-a,.56),'Concrete')
for y in (-6,6):
 for a,b in [(-6,-1.8),(1.8,6)]:box('PitCoping',((a+b)/2,y,-.32),(b-a,.16,.56),'Concrete')
def rail(a,b):
 a,b=Vector(a),Vector(b);length=(b-a).length
 beam('Railings',a+Vector((0,0,1.07)),b+Vector((0,0,1.07)),.08,.08,'PaintedSteel')
 beam('Railings',a+Vector((0,0,.53)),b+Vector((0,0,.53)),.055,.055,'PaintedSteel')
 count=max(1,math.ceil(length/1.2))
 for i in range(count+1):
  p=a+(b-a)*i/count;box('Railings',p+Vector((0,0,.535)),(.08,.08,1.07),'PaintedSteel')
  box('Railings',p+Vector((0,0,.012)),(.17,.17,.024),'BareSteel')
for x in (-6.08,6.08):
 for a,b in [(-6.08,-2.10),(2.10,6.08)]:rail((x,a,0),(x,b,0))
for y in (-6.08,6.08):
 for a,b in [(-6,-1.9),(1.9,6)]:rail((a,y,0),(b,y,0))
def stair_rail(axis,sign,side,width):
 # Posts sit INSIDE the stair well, each base on its actual horizontal tread.
 # The previous outer-edge posts sat in the solid raised floor while descending.
 def point(t,z):return Vector((sign*t,side*(width/2-.14),z) if axis==0 else (side*(width/2-.14),sign*t,z))
 a,b=point(8.52,0),point(5.88,-.60)
 for offset,size in ((1.07,.070),(.53,.045)):
  beam('Railings',a+Vector((0,0,offset)),b+Vector((0,0,offset)),size,size,'PaintedSteel')
 for t,floor in ((8.52,0),(8.10,-.15),(7.50,-.30),(6.90,-.45),(6.30,-.60),(5.88,-.60)):
  p=point(t,floor);top=1.07-.60*(8.52-t)/(8.52-5.88);height=top-floor-.026
  box('Railings',p+Vector((0,0,.012)),(.15,.15,.024),'BareSteel')
  box('Railings',p+Vector((0,0,.026+height/2)),(.06,.06,height),'PaintedSteel')
  for dx in (-.050,.050):
   for dy in (-.050,.050):box('Railings',p+Vector((dx,dy,.029)),(.014,.014,.010),'BareSteel')
for axis,width in ((0,4.),(1,3.6)):
 for sign in (-1,1):
  for side in (-1,1):stair_rail(axis,sign,side,width)
for i,a in enumerate(outline):
 b=outline[(i+1)%len(outline)];openings=[]
 if a[0]==b[0] and abs(a[0])==12:openings=[dict(center=8,width=3.,height=2.8)]
 wall_segment(a,b,6.1,openings,tiles=False)
prism('Roof',outline,6.1,6.37,'Concrete')
for sign in (-1,1):
 a,b=sorted((sign*12.,sign*14.));box('Floors',((a+b)/2,0,-.15),(2.,4.5,.3),'Concrete')
 wall_segment((a,-2.25),(b,-2.25),3.4,tiles=False);wall_segment((b,2.25),(a,2.25),3.4,tiles=False)
 x=sign*14;wall_segment((x,-2.25),(x,2.25),3.4,[dict(center=2.25,width=3.,height=2.8)],tiles=False)
 box('Roof',((a+b)/2,0,3.53),(2.28,4.78,.26),'Concrete')
 if CFG.get('sample_map'):
  box('SamplePortCaps',(x+sign*.09,0,1.4),(.14,3.,2.8),'PaintedSteel')
for x in (-7.25,7.25):beam('CeilingBeams',(x,-11.6,5.85),(x,11.6,5.85),.22,.38,'Concrete')
for y in (-7.25,7.25):beam('CeilingBeams',(-11.6,y,5.85),(11.6,y,5.85),.22,.38,'Concrete')
for x in (-11.7,11.7):
 for y in (-7.,7.):box('Columns',(x,y,3),(.32,.36,6),'Concrete')
# Eight-sided overhead cable route with open rungs and separate supported conduits.
ring=[(-7,-4.8),(-4.8,-7),(4.8,-7),(7,-4.8),(7,4.8),(4.8,7),(-4.8,7),(-7,4.8)]
for i,a in enumerate(ring):
 b=ring[(i+1)%len(ring)];v=Vector((b[0]-a[0],b[1]-a[1],0));length=v.length;v.normalize();n=Vector((-v.y,v.x,0))
 p=Vector((*a,4.75));q=Vector((*b,4.75))
 for s in (-1,1):beam('CableTrays',p+n*s*.22,q+n*s*.22,.055,.13,'BareSteel')
 for j in range(math.ceil(length/.4)+1):
  r=p+(q-p)*j/math.ceil(length/.4);beam('CableTrays',r-n*.21,r+n*.21,.025,.035,'BareSteel')
 for s in (-.13,0,.13):detail.tube('Conduits',[p+n*s+Vector((0,0,.025)),q+n*s+Vector((0,0,.025))],.025,'Rubber',10)
 for t in (.15,.85):
  r=p+(q-p)*t
  for s in (-1,1):beam('CableHangers',r+n*s*.28,r+n*s*.28+Vector((0,0,1.30)),.024,.024,'BareSteel')
# Wall-side plinths and rear frames leave the service apron to the player.
for bay in CFG['equipment_bays']:
 x,y,_=bay['center'];width=bay['width'];depth=bay['depth'];vertical=abs(x)>9;angle=math.pi/2 if vertical else 0
 box('EquipmentBases',(x,y,.08),(width,depth,.16),'PaintedSteel',angle)
 rear=depth/2-.075
 for offset in (-width/2+.08,width/2-.08):
  p=(x+(-rear if x<0 else rear),y+offset,1.55) if vertical else (x+offset,y-rear,1.55)
  box('BayFrames',p,(.10,.10,3.10),'BareSteel')
 p=(x+(-rear if x<0 else rear),y,3.1) if vertical else (x,y-rear,3.1)
 box('BayFrames',p,(width+.06,.10,.10),'BareSteel',angle)
 # Rear infill is a service mounting surface, not a substitute rack model.
 p=(x+(-rear if x<0 else rear),y,1.55) if vertical else (x,y-rear,1.55)
 box('BayPanels',p,(width-.18,.05,2.88),'Panel',angle)
# Dead display wall facing the dispatch floor, with visible frame depth and mounts.
for x in (-2.25,0,2.25):
 box('DisplayFrames',(x,10.65,3.5),(2.10,.25,1.28),'PaintedSteel')
 box('DisplayScreens',(x,10.515,3.5),(1.94,.018,1.12),'Screen')
 for dx in (-.63,.63):box('DisplayMounts',(x+dx,11.2,3.5),(.10,1.0,.16),'BareSteel')
box('DisplayFrames',(0,10.7,2.65),(6.8,.18,.08),'BareSteel')
for lamp in CFG['lights']:
 x,y,z=lamp['position'];ceiling=3.4 if abs(x)>12 else 6.1
 for dx in (-.46,.46):beam('LampHangers',(x+dx,y,z+.18),(x+dx,y,ceiling-.02),.018,.018,'BareSteel')
EXPORT_BLEND_NAME='AbandonedDataArchive_Structure.blend'
exec(compile((SCRIPT_DIR/'export_geometry.py').read_text(encoding='utf-8'),str(SCRIPT_DIR/'export_geometry.py'),'exec'))
