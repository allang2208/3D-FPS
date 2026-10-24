"""Dimensioned civic frontage and moored ferries, reusing the authored V17 city."""
import bpy,ast,json,math,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'RefinementV17/ArchitecturalNight_Source.blend'))
scene=bpy.context.scene;groups={};ATLAS_METRES=(4.,4.);xf=None
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('face','box','beam')],type_ignores=[]),'retained_geometry','exec'),globals())
baseface=face
def face(g,vs,mat='Metal',uv=None):
 if uv is None:
  normal=(Vector(vs[1])-Vector(vs[0])).cross(Vector(vs[2])-Vector(vs[0]));axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=axis]
  uv=[(v[axes[0]]/4,v[axes[1]]/4) for v in vs]
 if xf:
  x,y,c,s=xf;vs=[(x+c*a-s*b,y+s*a+c*b,z) for a,b,z in vs]
 baseface(g,vs,mat,uv)
def pose(x=0,y=0,angle=0):
 global xf
 xf=(x,y,math.cos(angle),math.sin(angle))
def reset():
 global xf
 xf=None
def rail(g,a,b,z,h=1.35,gap=None):
 a=Vector(a);b=Vector(b);v=b-a;count=max(1,math.ceil(v.length/4))
 for j in range(count+1):
  p=a+v*j/count;beam(g,(p.x,p.y,z),(p.x,p.y,z+h),.21,.21,'Metal')
 for hh,ww in [(h,.23),(.55,.12)]:beam(g,(a.x,a.y,z+hh),(b.x,b.y,z+hh),ww,ww,'Metal')
def planter(g,x,y,z,w=4.4,d=1.9):
 for xx in (-w/2+.12,w/2-.12):box(g,(x+xx,y,z+.5),(.24,d,1),'Metal')
 for yy in (-d/2+.12,d/2-.12):box(g,(x,y+yy,z+.5),(w-.48,.24,1),'Metal')
 box(g,(x,y,z+.85),(w-.52,d-.52,.16),'Rubber')
 # Solid clipped hedge volumes; no alpha foliage or unstable subpixel sprites.
 for i in range(3):
  xx=x+(i-1)*w*.28
  rings=[[(xx+math.cos(k*math.tau/8)*rr,y+math.sin(k*math.tau/8)*rr*.65,zz) for k in range(8)] for zz,rr in [(z+.9,.75),(z+1.6,1.),(z+2.15,.45)]]
  for low,high in zip(rings,rings[1:]):
   for k in range(8):face(g,[low[k],low[(k+1)%8],high[(k+1)%8],high[k]],'Leaves')
  face(g,rings[-1],'Leaves')
def bench(g,x,y,z,w=4.8):
 for xx in (-w*.35,w*.35):box(g,(x+xx,y,z+.38),(.35,1,.76),'Metal')
 for j in range(4):box(g,(x,y-.45+j*.3,z+.85),(w,.24,.18),'Copper')
 box(g,(x,y+.5,z+1.4),(w,.2,.9),'Metal')
def cylinder(g,x,y,z,r,h,role='Metal',sides=12):
 rings=[[(x+math.cos(k*math.tau/sides)*r,y+math.sin(k*math.tau/sides)*r,zz) for k in range(sides)] for zz in (z,z+h)]
 face(g,rings[0][::-1],role);face(g,rings[1],role)
 for k in range(sides):face(g,[rings[0][k],rings[0][(k+1)%sides],rings[1][(k+1)%sides],rings[1][k]],role)

# Use exactly the existing V16 road centreline, with tree gaps as entrance anchors.
raw=[Vector((x,y,0)) for x,y in SHORE[2:6]];points=[]
for i in range(len(raw)-1):
 a=raw[max(i-1,0)];b=raw[i];c=raw[i+1];d=raw[min(i+2,len(raw)-1)]
 for j in range(48):
  t=j/48;points.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
points.append(raw[-1])
def station(i,n=0):
 t=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized();normal=Vector((-t.y,t.x,0))
 return points[i]+normal*n,t,normal
rows=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings'];lobbies=[]
for index in LOBBY_ROWS:
 r=rows[index];x=r['x'];y=r['y']-r['depth']*.565;w=min(27,r['width']*.62);g='Frontage_'+str(len(lobbies)//4)
 pose(x,y)
 # Ground slab stops outside the existing podium. Its entrance is a supported extension.
 box(g,(0,-7.6,5.37),(w,13.7,.74),'Paving')
 box(g,(0,-2.4,8.4),(11,4.5,5.3),'Metal')
 box(g,(0,-4.72,8.2),(8.8,.18,4.9),'Glass')
 for xx in (-4.5,0,4.5):box(g,(xx,-4.86,8.2),(.22,.24,4.9),'Ivory')
 box(g,(0,-4.9,10.85),(9.4,.26,.5),'Teal')
 box(g,(0,-4,11.5),(15,7.5,.65),'Metal')
 for xx in (-6.8,6.8):beam(g,(xx,-7,5.74),(xx,-7,11.2),.35,.4,'Metal')
 box(g,(0,-7.82,11.15),(13,.22,.22),'Warm')
 # Separate full-height jambs and recessed horizontal mechanical canopy seams.
 for xx in (-6,-3,0,3,6):box(g,(xx,-4,11.86),(.13,6.8,.12),'Copper')
 for side in (-1,1):
  planter(g,side*(w*.5-3),-10,5.74,3.8,1.7)
  bench(g,side*(w*.5-3),-6.6,5.74,3.8)
 reset()
 target=Vector((x,y-14.45,0));i=min(range(3,len(points)-3,3),key=lambda j:(station(j,45)[0]-target).length_squared)
 start,t,n=station(i,45);finish=target;direction=(finish-start).normalized();cross=Vector((-direction.y,direction.x,0))*3.2
 # Shallow ramp meets V16's back pavement; no freestanding lane across car traffic.
 corner=[start+cross,start-cross,finish-cross,finish+cross]
 face(g,[(p.x,p.y,z) for p,z in zip(corner,[5.37,5.37,5.74,5.74])],'Paving')
 for side in (-1,1):
  a=start+cross*side;b=finish+cross*side
  beam(g,(a.x,a.y,5.42),(b.x,b.y,5.79),.15,.12,'Metal')
 lobbies.append(dict(building_index=index,source_center=[x,y],road_station=i,approach_length_m=(finish-start).length*1.25))

# Six spaced lookouts. Broad dark roof with warm undersides, no skyline-sized neon.
for j,i in enumerate([12,33,57,78,108,132]):
 p,t,n=station(i,4);pose(p.x,p.y,math.atan2(t.y,t.x));g='Lookouts_'+str(j//3)
 box(g,(0,0,5.45),(24,6.6,.7),'Paving')
 # Two low entrance treads on the road side keep the raised seat terrace connected.
 box(g,(0,3.65,5.22),(8,1.2,.44),'Paving');box(g,(0,4.25,5.12),(8,1.2,.24),'Paving')
 for xx in (-10.5,10.5):
  for yy in (-2.4,2.4):beam(g,(xx,yy,5.8),(xx,yy,11.6),.38,.45,'Metal')
 box(g,(0,0,11.9),(25,8,.55),'Metal')
 for xx in range(-10,11,2):box(g,(xx,0,12.22),(.55,7.8,.14),'Copper')
 for yy in (-3.65,3.65):box(g,(0,yy,11.59),(21,.25,.2),'Warm')
 bench(g,-6.6,.4,5.8);bench(g,6.6,.4,5.8)
 for xx in (-10.2,10.2):planter(g,xx,-.4,5.8,3,2.4)
 rail(g,(-12,-3.15,0),(12,-3.15,0),5.8)
 for side in (-1,1):rail(g,(side*12,-3.1,0),(side*12,2.6,0),5.8)
 # Sign has a sculpted numeral made of solid segments rather than another billboard card.
 box(g,(11,3.2,7.8),(1.6,.6,4),'Metal');box(g,(11,2.86,8.7),(.8,.08,1.35),'Teal')
 reset()

def ferry(g,x,y):
 pose(x,y)
 # V-bottom, chine and flare are separate hull sections; bow points toward the apartment.
 sections=[(-20,.45),(-17,2.6),(-10,4.5),(8,5.0),(16,4.6),(18,4.)]
 rings=[]
 for yy,w in sections:
  rings.append([(-w*.45,yy,-1.8),(w*.45,yy,-1.8),(w,yy,.65),(w,yy,2.45),(-w,yy,2.45),(-w,yy,.65)])
 for a,b in zip(rings,rings[1:]):
  for k in range(6):face(g,[a[k],b[k],b[(k+1)%6],a[(k+1)%6]],'Metal' if k in (0,1,5) else 'Ivory')
 face(g,rings[0][::-1],'Ivory');face(g,rings[-1],'Ivory')
 # Cabin has a sloped windshield and solid window mullions.
 front=-10;back=12;low=2.6;high=6.7
 corners=[(-3.8,front,low),(3.8,front,low),(3.8,back,low),(-3.8,back,low),(-3.5,front+2.3,high),(3.5,front+2.3,high),(3.5,back-.8,high),(-3.5,back-.8,high)]
 for ids in [(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:face(g,[corners[k] for k in ids],'Glass')
 for k in range(4):beam(g,corners[k],corners[k+4],.2,.22,'Ivory')
 for side in (-1,1):
  for yy in (-6,-2,2,6,10):beam(g,(side*3.82,yy,2.7),(side*3.55,yy,6.7),.18,.2,'Ivory')
  box(g,(side*3.85,1,3.1),(.22,21,.8),'Ivory')
  box(g,(side*3.87,1,3.55),(.13,21,.18),'Teal')
 box(g,(0,1.8,6.96),(7.7,20.7,.5),'Ivory');box(g,(0,4,7.26),(6,11,.12),'Glass')
 for yy in (0,4,8):box(g,(0,yy,7.35),(5.8,.18,.12),'Metal')
 box(g,(0,-6.7,6.83),(6.8,.2,.2),'Warm')
 for side in (-1,1):
  box(g,(side*4,10,6.5),(.22,.5,.3),'Red' if side<0 else 'Teal')
  rail(g,(side*4.1,12.5,0),(side*3.7,17.4,0),2.45,.95)
 # Small supported sensor mast and two stern electric drive housings.
 beam(g,(0,8,7.25),(0,8,9.1),.2,.2,'Metal');box(g,(0,8,9.2),(1.7,.45,.25),'Ivory')
 for xx in (-2.3,2.3):box(g,(xx,17,-.1),(1.6,2.1,2),'Metal')
 reset()

for j,(x,y) in enumerate(PIERS):
 pose(x,y);g='Terminal_'+str(j)
 # Keep the existing roof and seating. Add perimeter detail with a real boarding gap.
 rail(g,(-26,-133,0),(26,-133,0),3.9)
 rail(g,(-26,-133,0),(-26,-87,0),3.9)
 rail(g,(26,-133,0),(26,-117,0),3.9)
 rail(g,(26,-107,0),(26,-87,0),3.9)
 for xx in (-25,25):
  for yy in (-129,-93):
   cylinder(g,xx,yy,3.9,.45,.7);box(g,(xx,yy,4.65),(1.7,.4,.3),'Metal')
 for yy in (-126,-118,-102,-94):box(g,(27.3,yy,1.8),(.9,2.5,3.3),'Rubber')
 # Dock identification pylon, inset status lens and integrated low-brightness strips.
 box(g,(-18,-93,6.5),(3,2.4,5.2),'Metal');box(g,(-18,-94.27,7.3),(2.1,.1,2.4),'Glass')
 for k in range(j+1):box(g,(-18.7+k*.65,-94.36,8.1),(.3,.08,.8),'Teal')
 for xx in (-10,10):
  beam(g,(xx,-90,3.9),(xx,-90,8.7),.3,.3,'Metal')
 box(g,(0,-90,8.8),(20.5,.75,.65),'Metal');box(g,(0,-90.42,8.73),(18,.15,.25),'Warm')
 if j<2:
  # Pier x=27 -> vessel near edge x=33, with 6 m water gap and sloping bridge.
  for yy in (-114.2,-111.8):beam(g,(27,yy,3.95),(33.2,yy,2.63),.24,.24,'Metal')
  face(g,[(27,-114.2,3.95),(33.2,-114.2,2.63),(33.2,-111.8,2.63),(27,-111.8,3.95)],'Paving')
  for yy in (-114.2,-111.8):
   beam(g,(27,yy,5.1),(33.2,yy,3.8),.16,.16,'Metal')
   for xx,zz in [(27,3.95),(33.2,2.63)]:beam(g,(xx,yy,zz),(xx,yy,zz+1.15),.13,.13,'Metal')
 reset()
 if j<2:ferry('MooredFerries',x+38,y-113)

# Retained physically based surface sources, plus one new seamless paving family.
mats={}
for role,(rgb,rough,metal,glow) in SURFACES.items():
 m=bpy.data.materials.new('AP18_'+role);m.use_nodes=True;mats[role]=m
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for key,value in [('Base Color',(*rgb,1)),('Roughness',rough),('Metallic',metal),('Emission Color',(*rgb,1)),('Emission Strength',glow)]:p.inputs[key].default_value=value
 if role=='Paving':
  for suffix,pin in [('BC','Base Color')]:
   tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'Textures'/f'T_AP18_Paving_{suffix}.png'));tex.image.pack();m.node_tree.links.new(tex.outputs['Color'],p.inputs[pin])
out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,data in groups.items():
 me=bpy.data.meshes.new('AP18_'+key);me.from_pydata(data['v'],[],data['f']);me.update()
 ob=bpy.data.objects.new('AP18_'+key,me);scene.collection.objects.link(ob);ob.location.y=SHIFT
 order=list(dict.fromkeys(data['m']))
 for role in order:me.materials.append(mats[role])
 uv=me.uv_layers.new(name='SurfaceUV')
 for poly,role,coords in zip(me.polygons,data['m'],data['uv']):
  poly.material_index=order.index(role)
  for li,co in zip(poly.loop_indices,coords):uv.data[li].uv=co
 clone=ob.copy();clone.data=me.copy();scene.collection.objects.link(clone);clone.location=(0,0,0);clone.name='SM_AP18_'+key
 for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-(v.co.y+SHIFT)*1.25,(v.co.z-90)*1.25)
 bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone
 tri=clone.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 fbx=out/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=clone.name,fbx=str(fbx),triangles=len(clone.data.polygons),materials=order));bpy.data.objects.remove(clone,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'WaterfrontLife_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,lobbies=lobbies,lookouts=6,terminals=3,moored_ferries=2,new_dynamic_lights=0,new_tick_actors=0,shoreline_unchanged=True),indent=2),encoding='utf8')
print('AP18_WATERFRONT_AUTHORED',len(records),sum(r['triangles'] for r in records),flush=True)
