"""Measured residential envelope, solid facade modules and supported roof equipment.
No preview or acceptance render. Reuses existing project PBR sources.
"""
import bpy,bmesh,math,json,runpy
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
groups={};colliders={};window_count=0;balcony_count=0
roles=list(C['SURFACES'])+list(C['WINDOWS'])+list(C['ACCENTS'])
materials={}
for role in roles:
 m=bpy.data.materials.new(role);m.diffuse_color=(*C['SURFACES'].get(role,{}).get('color',(.025,.035,.05)),1);materials[role]=m
def face(g,points,role):
 d=groups.setdefault(g,dict(v=[],f=[],m=[]));start=len(d['v']);d['v'].extend(points);d['f'].append(tuple(range(start,start+len(points))));d['m'].append(role)
def box(g,p,s,role='Graphite',collision=False):
 x,y,z=p;a,b,c=[v/2 for v in s]
 v=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),(x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
 for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(g,[v[i] for i in ids],role)
 if collision:colliders.setdefault(g,[]).append(dict(p=p,s=s))
def cylinder(g,a,b,r,role='Steel',segments=24):
 a=Vector(a);b=Vector(b);axis=(b-a).normalized();ref=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((1,0,0));u=axis.cross(ref).normalized();v=axis.cross(u)
 rings=[[p+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*r for i in range(segments)] for p in (a,b)]
 face(g,[tuple(p) for p in reversed(rings[0])],role);face(g,[tuple(p) for p in rings[1]],role)
 for i in range(segments):j=(i+1)%segments;face(g,[tuple(rings[0][i]),tuple(rings[0][j]),tuple(rings[1][j]),tuple(rings[1][i])],role)
def sides(bounds):
 x0,y0,x1,y1=bounds
 return [('Front','y',1,y1,x0,x1),('Back','y',-1,y0,x0,x1),('West','x',-1,x0,y0,y1),('East','x',1,x1,y0,y1)]
def surf(g,side,u,z,w,h,depth,offset,role='Graphite'):
 _,axis,sign,coord,_,_=side
 box(g,(u,coord+sign*offset,z) if axis=='y' else (coord+sign*offset,u,z),(w,depth,h) if axis=='y' else (depth,w,h),role)
def window(g,side,u,z,width,height,occupancy,shade=False):
 global window_count
 window_count+=1
 # Deep charcoal reveal behind a raised structural frame; no luminous facade atlas.
 surf(g,side,u,z,width+.24,height+.24,.17,-.39,'Graphite')
 surf(g,side,u,z,width-.16,height-.16,.07,-.26,occupancy)
 for sign in (-1,1):
  surf(g,side,u+sign*width/2,z,.12,height+.12,.34,-.09,'Frame')
  surf(g,side,u,z+sign*height/2,width+.12,.12,.34,-.09,'Frame')
 surf(g,side,u,z,.065,height-.12,.20,-.13,'Steel')
 surf(g,side,u,z-height/2-.14,width+.42,.16,.56,.01,'Pearl')
 surf(g,side,u,z+height/2+.13,width+.42,.15,.66,.035,'Graphite')
 if shade:
  for j in range(4):surf(g,side,u,z+height/2-.18-j*.16,width-.22,.075,.12,-.12,'Frame')
def terrace(g,side,u,z,w):
 global balcony_count
 balcony_count+=1
 # Shallow non-playable residential balconies, physically supported at slab level.
 surf(g,side,u,z+.38,w+.5,.24,1.7,.63,'Concrete')
 surf(g,side,u,z+.48,w+.52,.07,1.73,.63,'Frame')
 surf(g,side,u,z+.90,w+.5,.22,.15,1.43,'Pearl')
 surf(g,side,u,z+1.47,w+.5,.07,.09,1.43,'Steel')
 for t in (-.5,0,.5):surf(g,side,u+t*w,z+.99,.055,.95,.07,1.43,'Frame')
 for sign in (-1,1):surf(g,side,u+sign*(w/2+.22),z+.99,.09,1.02,1.46,.70,'Frame')
def section(row):
 g=row['key'];bounds=row['bounds'];x0,y0,x1,y1=bounds;z0=row['z'];height=row['count']*C['FLOOR']
 box(g,((x0+x1)/2,(y0+y1)/2,z0+height/2),(x1-x0-1.20,y1-y0-1.20,height),'Graphite',True)
 for floor in range(row['count']):
  z=z0+floor*C['FLOOR'];level=row['floor_start']+floor
  box(g,((x0+x1)/2,(y0+y1)/2,z+.15),(x1-x0+.50,y1-y0+.50,.30),'Concrete')
  for side_index,side in enumerate(sides(bounds)):
   lo,hi=side[4:];n=max(3,round((hi-lo)/5.2));step=(hi-lo)/n
   surf(g,side,(lo+hi)/2,z+.65,hi-lo,.70,.42,-.08,'Graphite')
   surf(g,side,(lo+hi)/2,z+4.10,hi-lo,.60,.40,-.08,'Pearl' if level%4==0 else 'Graphite')
   for j in range(n):
    u=lo+(j+.5)*step;w=step-.86
    # Apartment occupancy is fixed in time and clustered over two floors.
    pick=((level//2)*13+j*7+side_index*17)%20
    role='GlassWarm' if pick<5 else 'GlassCool' if pick==5 else 'GlassDark'
    window(g,side,u,z+2.42,w,2.63,role,(j+level)%5==0)
    surf(g,side,lo+j*step,z+2.25,.48,3.9,.70,.02,'Pearl' if j in (0,n//2) else 'Graphite')
    if side[0]=='Front' and level%5==2 and j in (1,n-2):terrace(g,side,u,z,w)
   surf(g,side,hi,z+2.25,.48,3.9,.70,.02,'Pearl')
  # Grouped vertical service fins emphasize building structure without bright grids.
  for x in (x0+.32,x1-.32):box(g,(x,y0-.40,z+2.2),(.24,.75,4.4),'Frame')
 return g
for row in C['SECTIONS']:section(row)

# Podium: deep concrete footing, inhabited lobby window bays and entrance canopy.
g='Podium';x0,y0,x1,y1=(-9,-34,39,5);bottom=-110.1;top=-97.35
box(g,(15,-14.5,(bottom+top)/2),(46.8,37.8,top-bottom),'Concrete',True)
for side in sides((x0,y0,x1,y1)):
 lo,hi=side[4:];count=round((hi-lo)/5.5)
 for j in range(count):
  u=lo+(j+.5)*(hi-lo)/count
  if side[0]=='Front' and j==count//2:
   window(g,side,u,C['GROUND']+2.45,4.6,4.65,'GlassDark',False)
  else:window(g,side,u,-103.7,(hi-lo)/count-.85,5.1,'GlassWarm',False)
  surf(g,side,lo+j*(hi-lo)/count,-103.8,.5,8.7,.8,.4,'Pearl')
box(g,(15,-14.5,-97.55),(49.2,40.2,.50),'Frame')
box(g,(15,7.0,-102.3),(18,5.4,.50),'Graphite')
for x in (7,23):box(g,(x,8.8,-105.5),(.5,.5,6.3),'Steel')
box(g,(15,9.69,-102.44),(16,.08,.07),'GuideWarm')
box(g,(15,6.2,C['GROUND']+.06),(5.5,2.4,.12),'Concrete',True)
for x in (14.5,15.5):cylinder(g,(x,5.35,C['GROUND']+1.25),(x,5.35,C['GROUND']+2.45),.035,'Steel',16)

# Critical occupied floor: the interior already provides all walls/windows/collision.
# Only cladding on solid external faces and underside/roof returns is added here.
g='ApartmentInterface'
box(g,(15,-14.4,-.55),(42,31.6,.22),'Concrete',True)
box(g,(15,-14.4,6.04),(42,31.6,.32),'Pearl',True)
# Solid side/service cores carry the larger upper plate. The east window gets an
# open air court, rather than a new solid wing immediately outside its glazing.
for p,s in [((-3.25,-7.1,2.89),(5.5,15.4,5.78)),((15,-27.65,2.89),(42,4.7,5.78)),((33.3,-5.8,2.89),(5.4,12.8,5.78)),((33.3,-25.475,2.89),(5.4,9.05,5.78))]:box(g,p,s,'Graphite',True)
front=sides(C['MAIN'])[0]
for x in (-3.25,33.3):
 window(g,front,x,2.83,3.55,3.10,'GlassDark',True)
 for z,h in [(.60,1.2),(5.08,1.4)]:surf(g,front,x,z,5.4,h,.40,-.08,'Graphite')
# Front top cap stays above every existing pane. Side piers sit beyond the facade ends.
box(g,(15,.33,5.63),(30.7,.48,.18),'Frame')
box(g,(15,.56,5.65),(29.7,.055,.035),'GuideCyan')
for x in (-.47,30.47):box(g,(x,-.30,2.8),(.25,.9,5.6),'Pearl')
# West solid wall and the expanded gym wing: each skin follows its actual wall face.
box(g,(-.30,-7.45,2.75),(.12,14.9,5.5),'Graphite')
box(g,(-5.18,-19.14375,2.75),(.16,8.44,5.5),'Graphite')
box(g,(-2.65,-14.93,2.75),(5.15,.14,5.5),'Pearl')
box(g,(1.80,-23.40,2.75),(14.12,.16,5.5),'Graphite')
# East side window opening is kept entirely free, including a margin round its frame.
for ya,yb in [(-20.88,-18.30),(-12.40,.0)]:box(g,(30.30,(ya+yb)/2,2.75),(.12,yb-ya,5.5),'Graphite')
box(g,(30.30,-15.35,.28),(.12,5.90,.50),'Graphite')
box(g,(30.30,-15.35,5.39),(.12,5.90,.22),'Pearl')
# Back wall sections stop outside the existing entry/landing opening.
for xa,xb in [(8.95,17.35),(20.0,30.2)]:box(g,((xa+xb)/2,-20.92,2.75),(xb-xa,.14,5.5),'Graphite')
# Upper sunshade at each blank side wall; no full facade cover across the balcony view.
for y in (-4,-9,-19):box(g,(30.58,y,5.82),(.75,3.2,.12),'Frame')
# Existing balcony shape and usable rail are retained, with a new under-slab fascia.
box(g,(14.325,2.625,-.56),(14.24,5.30,.16),'Pearl')
box(g,(14.325,5.30,-.36),(14.24,.18,.35),'Frame')
box(g,(14.325,5.40,-.32),(12.4,.035,.035),'GuideWarm')
for x in (8.1,20.55):
 box(g,(x,2.25,-.68),(.25,4.9,.46),'Frame')
 box(g,(x,.42,-1.1),(.35,.85,1.1),'Concrete')
# Service strips on opaque wall portions, using real insets, conduits and fixing heads.
for x in (-5.28,30.41):
 for z in (1.2,3.8):
  box(g,(x,-19.55,z),(.15,1.15,.72),'Frame')
  for i in range(8):box(g,(x+(-.085 if x<0 else .085),-20.02+i*.135,z),(.06,.065,.56),'Steel')
for x in (-.43,30.43):cylinder(g,(x,-.65,.3),(x,-.65,5.45),.045,'Steel',16)

# Setback sky terrace and mechanical crown, with roof slab under every machine.
g='Crown';roof=76.6
box(g,(15,-13.5,roof+.12),(36.5,26.5,.24),'Concrete',True)
for side in sides((-3.25,-27,33.25,0)):
 lo,hi=side[4:];surf(g,side,(lo+hi)/2,roof+.85,hi-lo,1.3,.20,0,'Pearl')
 surf(g,side,(lo+hi)/2,roof+1.52,hi-lo,.09,.28,0,'Frame')
box(g,(15,-17.3,81.0),(17,11,8.6),'Graphite',True)
box(g,(15,-17.3,85.45),(17.8,11.8,.30),'Pearl')
for x in (7.1,22.9):box(g,(x,-11.65,81.1),(.25,.35,7.8),'Frame')
for j in range(32):box(g,(7.65+j*.46,-11.62,81.3),(.18,.20,5.7),'Steel')
for x in (1.8,8.2,25.8):
 box(g,(x,-7.0,roof+.45),(4.8,6.6,.65),'Concrete')
 box(g,(x,-7.0,roof+1.85),(4.3,6.1,2.2),'Graphite')
 for y in (-8.5,-5.5):
  cylinder(g,(x,y,roof+2.9),(x,y,roof+3.1),1.35,'Frame',40)
  cylinder(g,(x,y,roof+3.10),(x,y,roof+3.20),.25,'Steel',24)
  for i in range(10):
   angle=i*math.tau/10
   cylinder(g,(x+math.cos(angle)*.35,y+math.sin(angle)*.35,roof+3.16),(x+math.cos(angle+.25)*1.2,y+math.sin(angle+.25)*1.2,roof+3.16),.045,'Steel',8)
 for j in range(13):box(g,(x,-10.08,roof+1.0+j*.125),(3.7,.10,.055),'Frame')
 box(g,(x,-12.8,roof+.9),(1.2,5.2,1.1),'Steel')
box(g,(28,-21,roof+.30),(5.1,5.1,.36),'Concrete')
cylinder(g,(28,-21,roof+.48),(28,-21,roof+5.4),2.10,'Frame',48)
for z in (roof+.65,roof+5.1):cylinder(g,(28,-21,z),(28,-21,z+.15),2.17,'Steel',48)
for x in (12.8,17.2):
 cylinder(g,(x,-17.3,85.60),(x,-17.3,95.2),.18,'Steel',20)
 for z in (88.2,91.4):box(g,(x,-17.3,z),(.65,.35,1.40),'Pearl')
cylinder(g,(15,-17.3,85.60),(15,-17.3,101.4),.23,'Steel',24)
box(g,(15,-17.3,101.55),(.34,.34,.30),'GuideWarm')
for x in (5.7,24.3):
 box(g,(x,-1.1,roof+.75),(4.3,1.0,1.05),'Graphite')
 box(g,(x,-1.1,roof+1.25),(4.0,.78,.08),'Concrete')

out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
def uv_project(mesh):
 uv=mesh.uv_layers.new(name='UVMap');detail=mesh.uv_layers.new(name='PanelUV')
 for poly in mesh.polygons:
  axes=[a for a in range(3) if a!=max(range(3),key=lambda i:abs(poly.normal[i]))]
  points=[mesh.vertices[i].co for i in poly.vertices];lo=[min(p[a] for p in points) for a in axes];span=[max(p[a] for p in points)-lo[i] for i,a in enumerate(axes)]
  for li in poly.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;co=[p[a]-lo[i] for i,a in enumerate(axes)]
   uv.data[li].uv=co;detail.data[li].uv=[co[i]/max(span[i],.00001) for i in (0,1)]
def make_mesh(name,data):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in data['v']],[],[tuple(reversed(f)) for f in data['f']]);mesh.update()
 order=list(dict.fromkeys(data['m']))
 for role in order:mesh.materials.append(materials[role])
 for p,role in zip(mesh.polygons,data['m']):p.material_index=order.index(role)
 uv_project(mesh);ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);return ob,order
for key,data in list(groups.items()):
 name='SM_AP11_'+key;ob,order=make_mesh(name,data);export_objects=[ob]
 for i,row in enumerate(colliders.get(key,[])):
  cx,cy,cz=row['p'];bpy.ops.mesh.primitive_cube_add(size=1,location=(cx,-cy,cz));ucx=bpy.context.object;ucx.name='UCX_'+name+'_'+str(i).zfill(2);ucx.scale=row['s'];bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);export_objects.append(ucx)
 bpy.ops.object.select_all(action='DESELECT')
 for o in export_objects:o.select_set(True)
 bpy.context.view_layer.objects.active=ob
 # Triangulation remains an export modifier; planar UVs preserve each hard face.
 mod=ob.modifiers.new('Production triangulation','TRIANGULATE')
 path=out/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 triangles=sum(max(0,len(p.vertices)-2) for p in ob.data.polygons)
 records.append(dict(key=key,name=name,fbx=str(path),asset=C['BASE']+'/Meshes/'+name,triangles=triangles,materials=order,simple_collision_boxes=len(colliders.get(key,[])),nanite=True))
 for o in export_objects[1:]:o.hide_set(True);o.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ResidentialTower_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,window_modules=window_count,balconies=balcony_count,world_units='metres, final UE world positions',occupied_floor_clearance=C['PLAYABLE_CLEARANCE'],tests_run=False,rendered=False),indent=2),encoding='utf8')
print('AP11_TOWER_AUTHORED',window_count,balcony_count,sum(r['triangles'] for r in records),flush=True)
