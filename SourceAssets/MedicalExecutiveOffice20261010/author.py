"""Precision executive medical workstation. Author/export only, no renders or tests."""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
BASE='/Game/Dungeons/MedicalExecutiveOffice20261010'
LIB=PROJECT/'SourceAssets/DungeonReceptionHall20261006/Refine20261007'
sys.path.insert(0,str(LIB/'Scripts'));import office_geometry as g
g.OUT=OUT;g.BASE=BASE
RH='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Materials/M_RH2_'
g.MAP={k:RH+'Office_'+k for k in ('Steel','Rubber','Plastic','Keycaps','Legends','Display','Lamp','Copper')}
g.MAP.update(Wood=RH+'Wood',Paper=RH+'Paper',Blue=RH+'Blue',Seam=RH+'Seam',Leather=RH+'Leather',
 Paint=BASE+'/Materials/M_MedOffice_Graphite',Fabric=BASE+'/Materials/M_MedOffice_Fabric',
 Print=BASE+'/Materials/M_MedOffice_Print',Screen=BASE+'/Materials/M_MedOffice_Screen')
g.MATS={k:bpy.data.materials.get('RS_'+k) or bpy.data.materials.new('RS_'+k) for k in g.MAP}
# Primitive defaults must not precede the authored texture coordinates in UV0.
_finish=g.finish
def finish_with_primary_uv(obj,*args,**kwargs):
 for layer in list(obj.data.uv_layers):obj.data.uv_layers.remove(layer)
 return _finish(obj,*args,**kwargs)
g.finish=finish_with_primary_uv
ATLAS=json.loads((ROOT/'Config/atlas.json').read_text('utf8'))['regions']
pt=lambda p:(p[0]/100,-p[1]/100,p[2]/100)

def box(c,s,mat='Paint',edge=.25):return g.box(pt(c),tuple(v/100 for v in s),mat,min(edge,min(s)*.22)/100)
def cyl(c,r,h,mat='Steel',axis=(0,0,1),sides=32):return g.cylinder(pt(c),r/100,h/100,mat,(axis[0],-axis[1],axis[2]),sides)
def tube(points,r=.35,mat='Rubber',sides=10):
 ps=[Vector(pt(p)) for p in points];vs=[];fs=[];radius=r/100
 for i,p in enumerate(ps):
  tangent=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
  across=Vector((0,0,1)).cross(tangent)
  if across.length<.001:across=Vector((1,0,0))
  across.normalize();up=tangent.cross(across)
  vs.extend(p+radius*(math.cos(j*math.tau/sides)*across+math.sin(j*math.tau/sides)*up) for j in range(sides))
 for i in range(len(ps)-1):
  for j in range(sides):k=(j+1)%sides;fs.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
 fs.extend([tuple(range(sides-1,-1,-1)),tuple((len(ps)-1)*sides+j for j in range(sides))])
 return mesh('Continuous tubing',vs,fs,mat,metres=True,smooth=True)

def mesh(name,vertices,faces,mat,metres=False,smooth=False,edge=0):
 m=bpy.data.meshes.new(name);m.from_pydata(vertices if metres else [pt(p) for p in vertices],[],faces);m.update()
 bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
 o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o)
 for f in m.polygons:f.use_smooth=smooth
 return g.finish(o,mat,edge/100)

def prism(name,outline,z0,z1,mat,edge=.25):
 n=len(outline);vs=[(x,y,z) for z in (z0,z1) for x,y in outline]
 fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
 fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
 return mesh(name,vs,fs,mat,edge=edge)

def rotate(objects,center,yaw):
 rotation=Matrix.Rotation(math.radians(-yaw),4,'Z');c=Vector(pt(center))
 for o in objects:o.matrix_world=Matrix.Translation(c)@rotation@Matrix.Translation(-c)@o.matrix_world

def art(o,region,normal=(0,0,1)):
 """Assign print UVs to the actual cap face, with no overlapping decal polygon."""
 m=o.data;normal=Vector(normal);slot=len(m.materials);m.materials.append(g.MATS['Print'])
 axes=[i for i in range(3) if abs(normal[i])<.5];uv=m.uv_layers.active
 x,y,w,h=ATLAS[region]
 for f in m.polygons:
  if f.normal.dot(normal)<.999:continue
  points=[m.vertices[v].co for v in f.vertices];lo=[min(p[k] for p in points) for k in axes];hi=[max(p[k] for p in points) for k in axes]
  f.material_index=slot
  for li in f.loop_indices:
   p=m.vertices[m.loops[li].vertex_index].co;a,b=[(p[k]-lo[j])/max(.00001,hi[j]-lo[j]) for j,k in enumerate(axes)]
   uv.data[li].uv=((x+a*w)/2048,1-(y+(1-b)*h)/2048)

def emit(kind,hulls=()):
 obj=g.emit('SM_MedOffice_'+kind,hulls=[(pt(c),tuple(s/100 for s in size)) for c,size in hulls])
 record=g.records[-1];record.update(kind=kind,mesh=record.pop('asset'),collision_boxes=len(hulls),cast_shadow=True)
 return obj

# A continuous L-top: 240 x 110 cm primary desk + 60 x 90 cm printer return.
# The top and edge band occupy separate volumes, avoiding coincident cap faces.
outline=[(-120,-55),(180,-55),(180,35),(120,35),(120,55),(-120,55)]
prism('Walnut continuous L desktop',outline,74.3,77.5,'Wood',.8)
prism('Graphite floating edge band',outline,72.8,74.3,'Paint',.3)
for x in (-87,150):
 w=45 if x<0 else 54;cy=2 if x<0 else -10
 box((x,cy,37),(w,77,68),'Paint',.8)
 box((x,cy,4),(w-5,70,5),'Rubber',.35)
 # Three actual inset fronts with individual returns, pulls and lock escutcheon.
 for z,h in ((16,21),(39,20),(59,17)):
  box((x,cy+39, z),(w-2,2.2,h),'Wood',.28)
  for xx in (x-9,x+9):box((xx,cy+40.8,z+3),(1.7,2.6,1.8),'Steel',.3)
  tube([(x-9,cy+42,z+3),(x+9,cy+42,z+3)],.62,'Steel',16)
 cyl((x+w/2-6,cy+40.3,63),.95,.5,'Steel',axis=(0,1,0))
 box((x+w/2-6,cy+40.65,63),(.14,.22,.7),'Rubber',.01)
 for xx in (x-w/2+5,x+w/2-5):
  for yy in (cy-28,cy+28):cyl((xx,yy,1.5),2.4,3,'Rubber')
# Knee space stays open. Front modesty panel and under-table rail anchor equipment.
box((8,-42,44),(141,3.2,50),'Wood',.8)
for z in (29,45,61):box((8,-43.8,z),(139,.5,.6),'Steel',.1)
box((102,0,38),(5,84,72),'Steel',.55)
for y in (-34,34):cyl((102,y,1.6),3,3.2,'Rubber')
box((7,-39,67),(155,8,4),'Paint',.4)
box((27,-38,66.8),(50,7,6),'Rubber',.45)
for x in (9,20,31,42):
 box((x,-33.8,67),(7,1.3,3.7),'Plastic',.22)
 for dx in (-1.25,1.25):box((x+dx,-33.05,67),(.38,.15,1.1),'Rubber',.03)
for x in (-43,106):
 # Flush cable-port caps with a split rubber insert hide the cable entry.
 cyl((x,-39,77.62),3.2,.3,'Steel',sides=48)
 cyl((x,-39,77.82),2.65,.25,'Rubber',sides=48)
 box((x,-39,78.0),(4.6,.55,.18),'Paint',.05)
emit('ExecutiveDesk',[((0,0,75.15),(240,110,4.7)),((150,-10,75.15),(60,90,4.7)),
 ((-87,2,36),(45,79,72)),((150,-10,36),(54,79,72)),((8,-42,44),(141,3.2,50)),((102,0,37),(5,84,74))])

def pillow(name,c,width,depth,thickness,mat='Fabric',normal=(0,0,1),bulge=2):
 n=Vector(normal);right=Vector((1,0,0));up=n.cross(right);center=Vector(c)
 count=64;vs=[center+n*(thickness/2+bulge)];fs=[];rings=9
 def contour(a,r):
  co,si=math.cos(a),math.sin(a)
  return right*(math.copysign(abs(co)**.5,co)*width*.5*r)+up*(math.copysign(abs(si)**.5,si)*depth*.5*r)
 for i in range(1,rings+1):
  r=i/rings
  for j in range(count):vs.append(center+contour(j*math.tau/count,r)+n*(thickness/2+bulge*(1-r*r)))
 for j in range(count):fs.append((0,1+j,1+(j+1)%count))
 for i in range(rings-1):
  for j in range(count):a=1+i*count+j;b=1+i*count+(j+1)%count;fs.append((a,b,b+count,a+count))
 lower=len(vs)
 for j in range(count):vs.append(center+contour(j*math.tau/count,.97)-n*thickness/2)
 top=1+(rings-1)*count
 for j in range(count):k=(j+1)%count;fs.append((top+j,top+k,lower+k,lower+j))
 fs.append(tuple(range(lower+count-1,lower-1,-1)))
 obj=mesh(name,vs,fs,mat,smooth=True)
 seam=[center+contour(j*math.tau/128,.995)+n*(thickness/2-.35) for j in range(129)]
 tube(seam,.14,'Seam',6)
 return obj

# Executive ergonomic chair, local front -Y. Real shell, woven opening, lumbar and headrest.
for i in range(5):
 a=math.radians(18+i*72);d=Vector((math.cos(a),math.sin(a),0));cross=Vector((-d.y,d.x,0))
 points=[(d.x*r,d.y*r,z) for r,z in ((3,16),(12,15),(23,12),(33,7))]
 tube(points,2.2,'Steel',16)
 end=d*33
 cyl((end.x,end.y,6),1.7,6,'Paint')
 for side in (-1,1):
  p=end+cross*(side*2.5);cyl((p.x,p.y,3.4),3.4,3.1,'Rubber',axis=cross,sides=40)
  cyl((p.x+cross.x*side*1.6,p.y+cross.y*side*1.6,3.4),1.7,.28,'Paint',axis=cross,sides=32)
cyl((0,0,17),4.8,7,'Paint');cyl((0,0,27),2.6,15,'Steel',sides=48)
cyl((0,0,36),3.4,7,'Paint')
for z in (31.3,32,32.7,33.4):cyl((0,0,z),3.1,.4,'Rubber')
box((0,2,39),(27,29,6),'Paint',.9)
for x in (-10,10):
 for y in (-9,12):cyl((x,y,42.3),1,.7,'Steel',sides=16)
cyl((0,-15,38),5.5,9,'Rubber',axis=(0,1,0),sides=36)
for a in range(0,360,30):
 co,si=math.cos(math.radians(a)),math.sin(math.radians(a));tube([(co*5.7,-18,38+si*5.7),(co*5.7,-12,38+si*5.7)],.35,'Paint',6)
tube([(11,6,38),(23,10,39),(28,10,39)],.65,'Steel')
box((29,10,39),(7,4,1.7),'Rubber',.6)
pillow('Contoured waterfall seat',(0,-1,47),56,52,7,bulge=2.8)
pillow('Seat structural pan',(0,0,43),54,50,2.5,'Paint',bulge=.3)
for side in (-1,1):
 x=side*32
 tube([(side*21,12,41),(x,13,47),(x,11,65)],1.45,'Paint',16)
 box((x,10,61),(4.5,5,11),'Steel',.45);box((x,12.8,60),(2.1,1.2,4),'Rubber',.2)
 pillow('Adjustable armrest',(x,2,70),10,29,3,'Leather',bulge=.65)
for side in (-1,1):tube([(side*13,16,41),(side*18,27,50),(side*13,31,64),(side*8,34,91),(side*6,33,111)],1.8,'Paint',16)
def back(u,t):
 z=55+t*58;width=25+5*math.sin(math.pi*t)-2*t
 y=23+8*t-6*math.exp(-((t-.25)/.23)**2)+4*u*u
 return (u*width,y,z)
rim=[back(-1,i/40) for i in range(41)]+[back(-1+2*i/28,1) for i in range(1,29)]+[back(1,1-i/40) for i in range(1,41)]+[back(1-2*i/28,0) for i in range(1,29)]
tube(rim+[rim[0]],1.25,'Paint',16)
# Open weave is actual spaced, narrow geometry; it needs no translucent material.
for i in range(1,42):
 u=-1+2*i/42;tube([back(u,j/16) for j in range(17)],.105,'Fabric',6)
for i in range(1,44):
 t=i/44;tube([back(-1+2*j/18,t) for j in range(19)],.13,'Fabric',6)
pillow('Floating adjustable lumbar pad',(0,16.7,69),41,14,3.4,'Leather',normal=(0,-1,0),bulge=1.5)
for side in (-1,1):
 cyl((side*22,24,69),2.2,2.6,'Paint',axis=(1,0,0),sides=32)
 tube([(side*12,31,107),(side*12,33,118)],1,'Steel',12)
box((0,33,115),(32,5,5),'Paint',1)
pillow('Height adjustable headrest',(0,33,123),44,17,7,'Leather',normal=(0,-1,0),bulge=1.8)
emit('ErgonomicChair',[((0,0,24),(30,30,40)),((0,0,47),(56,52,10)),((0,26,87),(56,17,62)),((0,33,123),(44,10,18))])

# Matching upholstered visitor chair keeps the front of each consultation desk coherent.
for side in (-1,1):
 x=side*29
 tube([(x,26,2),(x,-24,2),(x,-28,7),(x,-28,40),(x,-23,45),(x,23,45),(x,27,62),(x,26,83)],1.3,'Steel',16)
 for y in (-20,19):box((x,y,1.5),(4,9,3),'Rubber',.6)
 pillow('Guest padded armrest',(x,0,64),7.5,33,3,'Leather',bulge=.6)
 tube([(x,-16,45),(x,-16,62)],1,'Steel')
pillow('Guest upholstered seat',(0,-1,45),52,49,6,'Fabric',bulge=1.5)
pillow('Guest curved backrest',(0,24,69),52,32,5,'Leather',normal=(0,-1,0),bulge=2)
emit('VisitorChair',[((0,0,44),(57,53,10)),((0,24,69),(53,9,34))])

# Reuse the existing detailed monitor, keyboard (native key legends), mouse,
# compact PC and corded telephone from the accepted station equipment recipe.
original=(PROJECT/'SourceAssets/StationWorkshop20261003/Scripts/author_workshop.py').read_text('utf8')
scope=dict(g=g,bpy=bpy,Vector=Vector,math=math)
exec(compile(original[original.index('REGIONS='):original.index('# Workshop fits')],'existing_equipment_helpers','exec'),scope)
scope['b']=lambda p:pt((p[0]-605,p[1]-77,p[2]))
refined=(PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Scripts/author_refine.py').read_text('utf8')
exec(compile(refined[refined.index('# Stand and monitor'):refined.index('# Handheld radio')],'reuse_clinical_computer_and_phone','exec'),scope)
# All replacement leads terminate in a connector, grommet or actual under-desk power rail.
for path,r in [([(-15,9.6,78.4),(-15,4,78.4),(10,-2,78.4),(41,-5,78.4),(67,-5,78.4),(84,-2,85.2)],.16),
 ([(21,12.4,79.1),(25,6,78.4),(46,2,78.4),(65,1,78.4),(84,-2,88)],.14),
 ([(-22,-21,104),(-22,-27,95),(-30,-32,80),(-43,-39,78.6),(-43,-39,68),(10,-36,67)],.23),
 ([(93,-1.4,80.3),(100,-14,78.4),(106,-30,78.5),(106,-39,78.6),(106,-39,67),(47,-36,67)],.24),
 ([(-59.5,-16.8,80.3),(-60,-25,78.4),(-50,-32,78.4),(-43,-39,78.5),(-43,-39,66.8)],.16)]:tube(path,r,'Rubber',8)

# Compact laser printer/scanner on the desk return, with an open paper outlet.
px,py,pz=150,-10,77.5
def pb(c,s,mat='Plastic',edge=.4):return box((px+c[0],py+c[1],pz+c[2]),s,mat,edge)
pb((0,0,5),(44,37,10),'Plastic',.8)
pb((0,-4,22),(44,29,20),'Plastic',.8)
for x in (-20,20):pb((x,15,15),(4,8,10),'Plastic',.4)
pb((0,7,15),(35,2,7),'Rubber',.2)
pb((0,20,9),(36,25,1.2),'Paint',.5)
paper=pb((0,21,10),(21,29.7,.25),'Paper',.04);art(paper,'Form')
pb((0,-1,33),(45,36,2.8),'Paint',.7)
pb((0,-1,35),(43,34,1.5),'Plastic',.6)
for x in (-15,15):cyl((px+x,py-16,pz+33),1.5,7,'Paint',axis=(1,0,0))
pb((-9,12,33.2),(13,9,1.2),'Rubber',.35)
pb((-9,12,33.9),(10,6.5,.3),'Display',.2)
for i in range(3):
 for j in range(3):pb((3+i*3.4,9+j*2.9,33.3),(2.4,2,.8),'Keycaps',.35)
for z in range(4,24,3):pb((22.05,-4,z),(.25,15,.65),'Rubber',.08)
pb((0,18.6,5),(32,.3,6),'Paint',.25);pb((0,19.1,7),(10,1,1.1),'Rubber',.3)
tube([(px+17,py-18,pz+8),(px+18,py-29,78.5),(123,-48,78.5),(106,-39,78.6),(106,-39,66.8)],.24,'Rubber',8)
emit('ClinicalElectronics')

def book(x,y,z,index=0,height=4,angle=0):
 start=len(g.parts);col=('Blue','Leather','Paint')[index%3]
 box((x,y,z+height/2),(22.8,30.6,height-.5),'Paper',.18)
 for zz in (z+.12,z+height-.12):
  cover=box((x,y,zz),(24,32,.24),col,.07)
  if zz>z+height/2:art(cover,'Book'+str(index%3))
 box((x-11.6,y,z+height/2),(.85,32,height),col,.32)
 for zz in (z+.7,z+height-.7):box((x-12.08,y,zz),(.08,28,.17),'Steel',.025)
 for j in range(1,max(2,int(height/.27))):box((x+11.43,y,z+.25+j*.24),(.035,30,.027),'Seam',.005)
 rotate(g.parts[start:],(x,y,z),angle)

def accessories(variant):
 # Supported, uneven piles instead of uniform scatter across the keyboard.
 z=77.5
 for i,h in enumerate((4.2,3.6,5.0) if variant==0 else (4.4,5.2)):
  book(-104+i*.55,12-i*.4,z,i,h,(-7,3,-3)[i]);z+=h
 z=77.5
 for i,h in enumerate((4.8,3.4,3.8)):
  book(53+i*.5,-23+i*.5,z,i+1,h,(5,-5,1)[i]);z+=h
 # A writing mat, clipped consultation sheets, capped pen and desktop planner.
 box((-66,29,77.8),(38,37,.6),'Leather',.7)
 clipboard=box((-64,29,78.35),(23,32,.5),'Blue',.3)
 sheet=box((-64,29,78.7),(21,29.7,.16),'Paper',.035);art(sheet,'Form')
 box((-64,14.6,79),(8,2.5,.6),'Steel',.2)
 for x in (-67,-61):cyl((x,14.6,79.4),.6,2.9,'Steel',axis=(1,0,0),sides=20)
 cyl((-47,27,79),.46,14,'Blue',axis=(0,1,0));cyl((-47,19.5,79),.26,1.6,'Steel',axis=(0,1,0))
 tube([(-46.6,32,79.4),(-46.3,29,79.6)],.1,'Steel',6)
 planner=box((58,25,78.7),(28,19.6,2.4),'Paper',.3);art(planner,'Planner')
 # A stepped letter tray with real open fronts, folders and metal wire returns.
 for i in range(2):
  zz=78+i*4.7;box((94,-24,zz),(30,34,.7),'Paint',.28)
  for x in (79.4,108.6):box((x,-24,zz+1.6),(.7,34,3.2),'Steel',.16)
  box((94,-40.4,zz+1.6),(29,.7,3.2),'Steel',.15)
  folder=box((94,-22+i,zz+.7),(23,30,.5),'Blue',.15)
  form=box((94,-21+i,zz+1.1),(21,29,.3),'Paper',.06);art(form,'Form')
 # Pen cup with an open rolled rim and sparse mesh wall.
 cx,cy=40,10
 cyl((cx,cy,77.9),3.5,.8,'Paint')
 for a in range(0,360,20):
  co,si=math.cos(math.radians(a)),math.sin(math.radians(a));tube([(cx+co*3.3,cy+si*3.3,78),(cx+co*3.3,cy+si*3.3,87)],.14,'Steel',6)
 for zz in (78.2,82.5,86.8):tube([(cx+3.4*math.cos(j*math.tau/48),cy+3.4*math.sin(j*math.tau/48),zz) for j in range(49)],.22,'Steel',8)
 for i,(dx,dy) in enumerate(((-1,-1),(1,0),(-.5,1.3))):
  tube([(cx+dx,cy+dy,78.5),(cx+dx*1.5,cy+dy*1.5,93+i)],.38,'Blue' if i%2 else 'Paint',8)
  cyl((cx+dx*1.5,cy+dy*1.5,93+i),.4,.8,'Steel')
 # Task lamp with two pivots, head, underside diffuser and an anchored power lead.
 lx,ly=-94,-35
 cyl((lx,ly,78.2),7,1.4,'Paint',sides=48)
 tube([(lx,ly,78.9),(lx+2,ly,101),(lx+15,ly,116)],.85,'Steel',12)
 for x,zz in ((lx+2,101),(lx+15,116)):cyl((x,ly,zz),1.8,3,'Paint',axis=(0,1,0))
 box((lx+25,ly,116),(28,6,3),'Paint',.8)
 box((lx+25,ly,114.4),(24,4,.35),'Lamp',.12)
 tube([(lx,ly-5,78.3),(-83,-44,78.3),(-64,-44,78.3),(-43,-39,78.4)],.17,'Rubber',8)
 # A small upright engraved desk sign; print replaces its front face.
 plate=box((14,-42,83),(28,2,5.6),'Paint',.15);art(plate,'Nameplate',normal=(0,1,0))
 box((14,-42,78.2),(29,8,1.4),'Steel',.3)
 for x in (5,23):tube([(x,-42,78.9),(x,-42,80.3)],.35,'Steel')
 emit('DesktopDetails'+str(variant))
accessories(0);accessories(1)
for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MedicalExecutiveOffice.blend'))
(ROOT/'Config/geometry.json').write_text(json.dumps({'meshes':g.records,'desk_top_cm':77.5,'desk_footprint_cm':[300,110],
 'sources':{'equipment':'StationWorkshop20261003/RefineV2/Scripts/author_refine.py','surface_materials':'ReceptionHall20261006/Refine20261007'},'rendered':False},ensure_ascii=False,indent=2),encoding='utf8')
print('MEDICAL_EXECUTIVE_GEOMETRY_EXPORTED',len(g.records),flush=True)
