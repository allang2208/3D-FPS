"""Static road/tree batches, three low-poly vehicles and a closed GPU path texture."""
import bpy,math,json,sys,ast,random
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
groups={};ATLAS_METRES=(10.,10.);mats={}
for role in ['Asphalt','Concrete','Paint','Bark','Leaves','Metal','Cyan','Warm','Body','Glass','Tire','Headlamp','Tail']:
 m=bpy.data.materials.new(role);mats[role]=m
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('face','box','beam')],type_ignores=[]),'architectural_helpers','exec'),globals())
_face=face
phase=0.
def face(g,vs,mat='Metal',uv=None):
 if uv is None:
  n=(Vector(vs[1])-Vector(vs[0])).cross(Vector(vs[2])-Vector(vs[0]));axis=max(range(3),key=lambda i:abs(n[i]));xy=[i for i in range(3) if i!=axis];uv=[(v[xy[0]]/8,v[xy[1]]/8) for v in vs]
 _face(g,vs,mat,uv);groups[g].setdefault('phase',[]).append(phase)

def offset_path(points,d):
 out=[]
 for i,p in enumerate(points):
  a=Vector(points[max(0,i-1)]);b=Vector(points[min(len(points)-1,i+1)]);v=(b-a).normalized();out.append(Vector(p)+Vector((-v.y,v.x,0))*d)
 return out
# Central frontage, inside the existing bank and clear of the first row podiums.
raw=[Vector((x,y+AUTHOR_SHIFT_Y,0)) for x,y in SHORE[2:6]]
points=[]
for i in range(len(raw)-1):
 a=raw[max(i-1,0)];b=raw[i];c=raw[i+1];d=raw[min(i+2,len(raw)-1)]
 for j in range(48):
  t=j/48;points.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
points.append(raw[-1]);center=offset_path(points,26)
def ribbon(g,ds,z,role):
 a=offset_path(points,ds[0]);b=offset_path(points,ds[1])
 for i in range(len(points)-1):face(g,[(a[i].x,a[i].y,z),(a[i+1].x,a[i+1].y,z),(b[i+1].x,b[i+1].y,z),(b[i].x,b[i].y,z)],role)
ribbon('Roads',(10,42),5.35,'Concrete');ribbon('Roads',(14,38),5.42,'Asphalt')
for ds in [(13.7,14.1),(37.9,38.3),(25.7,26.3)]:ribbon('Roads',ds,5.46,'Paint')
# Paved end bulbs cover the semicircular traffic turnaround without extending
# another coplanar surface over the longitudinal road strip.
for end in [0,-1]:
 p=center[end];t=(center[1]-center[0]).normalized() if end==0 else (center[-1]-center[-2]).normalized()
 outward=t*(-1 if end==0 else 1);n=Vector((-t.y,t.x,0))
 for radius,z,role in [(16,5.35,'Concrete'),(12,5.42,'Asphalt')]:
  ring=[p+n*(radius*math.cos(math.pi*j/24))+outward*(radius*math.sin(math.pi*j/24)) for j in range(25)]
  for a,b in zip(ring,ring[1:]):
   vs=[(p.x,p.y,z),(a.x,a.y,z),(b.x,b.y,z)]
   if (a-p).cross(b-p).z<0:vs.reverse()
   face('Roads',vs,role)
# Build the closed path: outbound lane, semicircle, return lane, semicircle.
forward=offset_path(center,-5);back=offset_path(center,5);loop=list(forward)
tangent=(center[-1]-center[-2]).normalized();normal=Vector((-tangent.y,tangent.x,0))
for j in range(1,25):
 a=math.pi*j/24;loop.append(center[-1]-normal*(5*math.cos(a))+tangent*(5*math.sin(a)))
loop+=list(reversed(back[:-1]));tangent=(center[1]-center[0]).normalized();normal=Vector((-tangent.y,tangent.x,0))
for j in range(1,25):
 a=math.pi*j/24;loop.append(center[0]+normal*(5*math.cos(a))-tangent*(5*math.sin(a)))
loop.append(loop[0]);lengths=[0.]
for a,b in zip(loop,loop[1:]):lengths.append(lengths[-1]+(b-a).length)
length=lengths[-1]
def sample(t):
 distance=(t%1)*length;i=0
 while i<len(lengths)-2 and lengths[i+1]<distance:i+=1
 return loop[i].lerp(loop[i+1],(distance-lengths[i])/(lengths[i+1]-lengths[i]))
def tangent_at(t):return (sample(t+.00004)-sample(t-.00004)).normalized()
def world(p,z=5.44):return Vector(((-p.x+10)*1.25,p.y*1.25,(z-90)*1.25))
def worlddir(t):v=tangent_at(t);return Vector((-v.x,v.y,0))
size=2048;pixels=[]
for j in range(size):
 t=j/size;p=world(sample(t));d=worlddir(t);pixels.extend([p.x,p.y,d.x,d.y])
im=bpy.data.images.new('TrafficPath',width=size,height=1,alpha=True,float_buffer=True);im.alpha_mode='CHANNEL_PACKED';im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(pixels);im.file_format='OPEN_EXR';im.filepath_raw=str(R/'T_AP16_TrafficPath.exr');im.save()

rng=random.Random(16023)
def canopy(g,p,r,sz):
 # Solid six-sided crowns avoid leaf alpha shimmer at this viewing distance.
 rings=[]
 for z,rr in [(0,r*.68),(sz*.45,r),(sz,.25*r)]:
  rings.append([(p.x+math.cos(k*math.tau/7)*rr,p.y+math.sin(k*math.tau/7)*rr,p.z+z) for k in range(7)])
 for l in range(2):
  for k in range(7):face(g,[rings[l][k],rings[l][(k+1)%7],rings[l+1][(k+1)%7],rings[l+1][k]],'Leaves')
 face(g,rings[-1],'Leaves')
for i in range(2,len(points)-2,3):
 p=points[i];t=(points[i+1]-points[i-1]).normalized();n=Vector((-t.y,t.x,0))
 for side in [9,44]:
  a=p+n*side;g='Trees';h=rng.uniform(7.5,10.5)
  box(g,(a.x,a.y,5.55),(5.5,5.5,.4),'Concrete');beam(g,(a.x,a.y,5.7),(a.x,a.y,5.7+h*.6),.55,.55,'Bark')
  canopy(g,Vector((a.x,a.y,5.7+h*.4)),rng.uniform(2.4,3.3),h*.65)
 if i%6==2:
  a=p+n*11;beam('StreetFurniture',(a.x,a.y,5.5),(a.x,a.y,15),.45,.45,'Metal');beam('StreetFurniture',(a.x,a.y,15),(a.x+n.x*5,a.y+n.y*5,15),.4,.4,'Metal')
  box('StreetFurniture',(a.x+n.x*4,a.y+n.y*4,14.8),(2.8,1.2,.35),'Warm')
 # Visible dashed lane marks, spaced well above the subpixel regime.
 a=p+n*20;b=a+t*5;beam('Roads',(a.x,a.y,5.48),(b.x,b.y,5.48),.35,.025,'Paint')
 a=p+n*32;b=a+t*5;beam('Roads',(a.x,a.y,5.48),(b.x,b.y,5.48),.35,.025,'Paint')
for i in (18,71,124):
 p=points[i];t=(points[i+1]-points[i-1]).normalized();n=Vector((-t.y,t.x,0))
 # Short service access, paved turnouts and marked pedestrian crossings.
 for j in range(8):
  a=p+n*14+t*(j*.9-3.6);b=a+n*24;beam('Junctions',(a.x,a.y,5.49),(b.x,b.y,5.49),.48,.025,'Paint')
 a=p+n*38;b=p+n*52;v=t*7
 face('Junctions',[(q.x,q.y,5.43) for q in (a-v,b-v,b+v,a+v)],'Asphalt')
 for sign in (-1,1):
  q=p+n*41+t*sign*8;beam('StreetFurniture',(q.x,q.y,5.5),(q.x,q.y,10),.4,.4,'Metal');box('StreetFurniture',(q.x,q.y,10),(1.3,.5,1.8),'Metal');box('StreetFurniture',(q.x,q.y-.27,10.3),(.65,.12,.65),'Cyan')

# Three compact author-space vehicle prototypes: +X forward, +Y left.
vehicle_parts={}
for kind in ['Coupe','Shuttle','Freight']:
 phase=0.;g='Prototype_'+kind;length_car={'Coupe':5.5,'Shuttle':7.2,'Freight':6.4}[kind]
 box(g,(0,0,.8),(length_car,2.5,1),'Body');box(g,(-.35,0,1.65),(length_car*.53,2.2,1),'Glass')
 box(g,(-.35,0,2.2),(length_car*.54,2.27,.15),'Body')
 if kind=='Freight':box(g,(-1,0,1.9),(3.5,2.55,1.8),'Body')
 for x in [-length_car*.31,length_car*.31]:
  for y in [-1.3,1.3]:
   # Low-sided solid wheels, actual tires and hubs rather than light dots.
   rings=[[(x+math.cos(k*math.tau/10)*.55,yy,.55+math.sin(k*math.tau/10)*.55) for k in range(10)] for yy in [y-.15,y+.15]]
   for k in range(10):face(g,[rings[0][k],rings[0][(k+1)%10],rings[1][(k+1)%10],rings[1][k]],'Tire')
   face(g,rings[0][::-1],'Metal');face(g,rings[1],'Metal')
 for side in [-1,1]:
  box(g,(length_car/2+.02,side*.78,1),( .12,.7,.24),'Headlamp');box(g,(-length_car/2-.02,side*.78,1),(.12,.7,.25),'Tail')
 box(g,(0,0,.22),(length_car*.7,1.9,.18),'Metal');vehicle_parts[kind]=groups.pop(g)
for k,(kind,data) in enumerate(vehicle_parts.items()):
 for j in range(12):
  phase=(j*3+k)/36;p=world(sample(phase));forward=worlddir(phase);left=Vector((-forward.y,forward.x,0));g='Traffic_'+kind
  for ids,mat,uv in zip(data['f'],data['m'],data['uv']):
   vs=[]
   for index in ids:
    x,y,z=data['v'][index];q=p+forward*x*1.25+left*y*1.25+Vector((0,0,z*1.25));vs.append(tuple(q))
   face(g,vs,mat,uv)
phase=0;records=[];export=R/'Meshes';export.mkdir(exist_ok=True)
for name,data in groups.items():
 traffic=name.startswith('Traffic_');me=bpy.data.meshes.new(name)
 vs=data['v'] if traffic else [tuple(world(Vector(v),v[2])) for v in data['v']]
 # Final UE metre coordinates; reflect Y once for the FBX route.
 me.from_pydata([(v[0],-v[1],v[2]) for v in vs],[],data['f']);me.update();ob=bpy.data.objects.new('SM_AP16_'+name,me);scene.collection.objects.link(ob)
 order=list(dict.fromkeys(data['m']))
 for role in order:me.materials.append(mats[role])
 uv=me.uv_layers.new(name='SurfaceUV');uv2=me.uv_layers.new(name='TrafficPhase')
 for poly,role,coords,ph in zip(me.polygons,data['m'],data['uv'],data['phase']):
  poly.material_index=order.index(role)
  for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co;uv2.data[li].uv=(ph,0)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 fbx=export/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=name,name=ob.name,fbx=str(fbx),triangles=len(ob.data.polygons),traffic=traffic,materials=order))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'HarborStreets_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,route_length_m=length*1.25,cars=36,vehicle_types=3,tree_count=len(range(2,len(points)-2,3))*2,route_texture='T_AP16_TrafficPath.exr'),indent=2))
print('AP16_STREETS_AUTHORED',len(records),flush=True)
