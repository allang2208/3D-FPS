"""Rounded city traffic, with the original route/phase WPO contract retained.
Author units are metres, +X forward, +Y left; the existing city uses scale 1.25.
No rendering or gameplay is performed by this production script.
"""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent
OLD=R.parent/'CyberpunkApartmentRebuild20261022/RefinementV16'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
roles=['Body','Glass','Rubber','Alloy','Trim','Headlamp','DRL','Tail','Amber','Pool']
colors={'Body':(.15,.22,.25,1),'Glass':(.015,.036,.05,1),'Rubber':(.012,.014,.017,1),'Alloy':(.4,.44,.48,1),'Trim':(.035,.043,.05,1),'Headlamp':(.83,.92,1,1),'DRL':(.65,.83,1,1),'Tail':(.6,.006,.003,1),'Amber':(1,.2,.01,1),'Pool':(.5,.65,1,1)}
mats={}
for role in roles:
 m=bpy.data.materials.new(role);m.diffuse_color=colors[role];mats[role]=m
parts=[]

def adopt(o,name,role,smooth=True):
 o.name=name;o.data.materials.clear();o.data.materials.append(mats[role])
 for p in o.data.polygons:p.use_smooth=smooth
 parts.append(o);return o

def mesh(name,vs,fs,role='Body',face_roles=None):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);adopt(o,name,role)
 if face_roles:
  me.materials.clear()
  for r in roles:me.materials.append(mats[r])
  for p,r in zip(me.polygons,face_roles):p.material_index=roles.index(r)
 return o

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def bevel(o,width=.025,segments=3):
 activate(o);b=o.modifiers.new('Manufactured edge radius','BEVEL');b.width=width;b.segments=segments
 bpy.ops.object.modifier_apply(modifier=b.name)
 n=o.modifiers.new('Panel normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=40
 bpy.ops.object.modifier_apply(modifier=n.name)
 return o

def box(name,c,size,role='Body',radius=.025):
 bpy.ops.mesh.primitive_cube_add(size=1,location=c);o=bpy.context.object;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);adopt(o,name,role)
 if radius:bevel(o,min(radius,min(size)*.45),3)
 return o

def pipe(name,ps,r,role='Trim',sides=8):
 vs=[];fs=[]
 for i,p in enumerate(ps):
  t=(Vector(ps[min(i+1,len(ps)-1)])-Vector(ps[max(0,i-1)])).normalized()
  n=t.cross(Vector((0,0,1)))
  if n.length<.01:n=t.cross(Vector((0,1,0)))
  n.normalize();b=t.cross(n).normalized()
  vs.extend(tuple(Vector(p)+r*(n*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))) for j in range(sides))
 for i in range(len(ps)-1):
  for j in range(sides):a=i*sides+j;c=i*sides+(j+1)%sides;fs.append((a,c,c+sides,a+sides))
 fs.extend([tuple(reversed(range(sides))),tuple(range((len(ps)-1)*sides,len(ps)*sides))])
 return mesh(name,vs,fs,role)

def interp(ctrl,x):
 for i in range(len(ctrl)-1):
  if x<=ctrl[i+1][0]+1e-7:
   a=ctrl[max(0,i-1)];b=ctrl[i];c=ctrl[i+1];d=ctrl[min(i+2,len(ctrl)-1)];t=(x-b[0])/(c[0]-b[0])
   return [(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t)) for k in range(1,len(b))]
 return list(ctrl[-1][1:])

def rounded_section(width,lo,hi,r):
 out=[];r=min(r,(hi-lo)*.45,width*.3)
 for cy,cz,start in [(width-r,hi-r,0),(-width+r,hi-r,90),(-width+r,lo+r,180),(width-r,lo+r,270)]:
  for j in range(6):
   a=math.radians(start+j*90/5);out.append((cy+r*math.cos(a),cz+r*math.sin(a)))
 return out

def body(kind,L,W,H,wheelx,wr):
 # Width taper and hood/deck crown are lofted, not a bevel on a large box.
 ctrl=[(-L/2,W*.38,.72*H),(-L*.46,W*.46,.83*H),(-L*.34,W*.5,.94*H),(-L*.12,W*.5,H),(L*.16,W*.495,H),(L*.34,W*.48,.93*H),(L*.46,W*.44,.84*H),(L/2,W*.37,.76*H)]
 vs=[];fs=[];nx=65;ns=24
 for i in range(nx):
  x=-L/2+L*i/(nx-1);w,z=interp(ctrl,x)
  vs.extend((x,y,zz) for y,zz in rounded_section(w,.24,z,.14))
 for i in range(nx-1):
  for j in range(ns):a=i*ns+j;b=i*ns+(j+1)%ns;fs.append((a,b,b+ns,a+ns))
 fs.extend([tuple(reversed(range(ns))),tuple(range((nx-1)*ns,nx*ns))])
 o=mesh(kind+'_SculptedBody',vs,fs)
 # Through-body wheel openings remove bodywork above/inside the tires.
 for x in wheelx:
  bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=wr+.055,depth=W+1,location=(x,0,wr+.02),rotation=(math.pi/2,0,0));c=bpy.context.object
  activate(o);mod=o.modifiers.new('Wheel opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=c
  bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(c,do_unlink=True)
 bevel(o,.012,2)
 return o

def cabin(kind,ctrl,W,base,pillar,front_glass,rear_glass):
 vs=[];fs=[];rs=[];nx=65;ns=24
 for i in range(nx):
  x=ctrl[0][0]+(ctrl[-1][0]-ctrl[0][0])*i/(nx-1);w,h=interp(ctrl,x)
  section=rounded_section(w,base,h,.10)
  # Roof pinches inward while beltline remains wide, giving a tumblehome.
  for y,z in section:
   t=max(0,min(1,(z-base)/max(.01,h-base)));vs.append((x,y*(1-.14*t),z))
 for i in range(nx-1):
  x=(vs[i*ns][0]+vs[(i+1)*ns][0])*.5
  for j in range(ns):
   a=i*ns+j;b=i*ns+(j+1)%ns;fs.append((a,b,b+ns,a+ns))
   z=(vs[a][2]+vs[b][2])*.5;y=(abs(vs[a][1])+abs(vs[b][1]))*.5
   w,h=interp(ctrl,x);side=y>w*.68 and z>base+.105 and z<h-.075
   if kind=='Freight' and x<.50:side=False
   slope=(x>front_glass or x<rear_glass) and z>h-.15
   is_pillar=any(abs(x-p)<.052 for p in pillar)
   rs.append('Glass' if (side or slope) and not is_pillar else 'Body')
 fs.extend([tuple(reversed(range(ns))),tuple(range((nx-1)*ns,nx*ns))]);rs+=['Body','Body']
 return mesh(kind+'_CurvedCabin',vs,fs,face_roles=rs)

def wheel(kind,x,y,r,width,side):
 ns=40;vs=[];fs=[]
 # Rounded sidewalls with a distinct tread band.
 profile=[(-width*.5,r*.76),(-width*.54,r*.88),(-width*.43,r*.98),(-width*.25,r),(width*.25,r),(width*.43,r*.98),(width*.54,r*.88),(width*.5,r*.76)]
 for yy,rr in profile:
  vs.extend((x+rr*math.cos(j*math.tau/ns),y+yy,r+.02+rr*math.sin(j*math.tau/ns)) for j in range(ns))
 for i in range(len(profile)-1):
  for j in range(ns):a=i*ns+j;b=i*ns+(j+1)%ns;fs.append((a,b,b+ns,a+ns))
 fs.extend([tuple(reversed(range(ns))),tuple(range((len(profile)-1)*ns,len(profile)*ns))])
 mesh(kind+'_Tire',vs,fs,'Rubber')
 facey=y+side*width*.53
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r*.68,depth=.035,location=(x,facey,r+.02),rotation=(math.pi/2,0,0));adopt(bpy.context.object,kind+'_BrakeDisc','Trim')
 ring=[(x+r*.70*math.cos(j*math.tau/48),facey+side*.025,r+.02+r*.70*math.sin(j*math.tau/48)) for j in range(49)]
 pipe(kind+'_Rim',ring,.022,'Alloy',6)
 for j in range(5):
  a=j*math.tau/5
  o=box(kind+'_Spoke',(x+r*.37*math.cos(a),facey+side*.035,r+.02+r*.37*math.sin(a)),(r*.57,.042,.045),'Alloy',.014);o.rotation_euler.y=-a
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.073,location=(x,facey+side*.035,r+.02));o=bpy.context.object;o.scale=(1,.3,1);adopt(o,kind+'_Hub','Alloy')

def make(kind):
 global parts
 parts=[]
 if kind=='Coupe':
  L,W,H,wr=4.90,1.91,.99,.365;wx=(-1.43,1.43);base=.89
  ctrl=[(-1.98,.62,.97),(-1.6,.80,1.13),(-.93,.85,1.47),(-.35,.86,1.51),(.38,.85,1.47),(.94,.83,1.23),(1.38,.77,.99)];pillars=[-.23];fg=.52;rg=-1.08
 elif kind=='Shuttle':
  L,W,H,wr=5.05,1.99,1.08,.402;wx=(-1.49,1.48);base=.98
  ctrl=[(-2.15,.78,1.11),(-1.83,.88,1.59),(-1.35,.90,1.78),(-.35,.90,1.81),(.43,.88,1.76),(1.00,.86,1.39),(1.31,.80,1.09)];pillars=[-.40,-1.35];fg=.54;rg=-1.85
 else:
  L,W,H,wr=5.85,2.05,1.14,.405;wx=(-1.72,1.66);base=1.02
  ctrl=[(-2.70,.83,1.23),(-2.58,.94,2.05),(-2.32,.96,2.28),(-.55,.96,2.31),(.53,.94,2.28),(1.04,.92,2.13),(1.67,.86,1.27),(1.89,.79,1.13)];pillars=[.47];fg=1.06;rg=-3
 body(kind,L,W,H,wx,wr);cabin(kind,ctrl,W,base,pillars,fg,rg)
 if kind=='Freight':
  # Cargo side panels use the same curved shell; shutlines sit on its surface.
  for s in [-1,1]:
   def side_point(x,z):
    w,h=interp(ctrl,x);return (x,s*(w*(1-.14*(z-base)/(h-base))+.009),z)
   pipe(kind+'_CargoDoorSeam',[side_point(x,z) for x,z in [(-2.25,1.18),(-2.25,1.90),(-2.20,2.10),(-1.5,2.14),(-.55,2.14),(.37,2.08),(.40,1.18)]],.007,'Trim',6)
   pipe(kind+'_SlideRail',[side_point(x,1.37) for x in [-2.25,-1.75,-1.1,-.55,.35]],.013,'Trim')
  pipe(kind+'_RearDoorSplit',[(-2.73,0,.82),(-2.73,0,1.14),(-2.59,0,1.95),(-2.43,0,2.20)],.012,'Trim')
 for s in [-1,1]:
  for x in wx:wheel(kind,x,s*(W*.5-.09),wr,.23,s)
  # Rounded sill, flush handles, mirrors, fine door shutlines.
  box(kind+'_Sill',(0,s*(W*.5-.06),.30),(wx[1]-wx[0]-.78,.10,.15),'Trim',.045)
  doorxs=[-.24,.78] if kind!='Freight' else [.48]
  for x in doorxs:
   y=s*(W*.5-.005)
   pipe(kind+'_DoorSeam',[(x,y,.45),(x,y,.82),(x,y,H-.02)],.007,'Trim',6)
   box(kind+'_Handle',(x-.22,y+s*.009,H-.055),(.15,.025,.027),'Alloy',.012)
  mx=1.02 if kind!='Freight' else 1.29;mz=1.13 if kind=='Coupe' else (1.37 if kind=='Shuttle' else 1.48)
  pipe(kind+'_MirrorStalk',[(mx,s*W*.43,mz-.04),(mx-.05,s*(W*.5+.07),mz)],.028,'Trim')
  box(kind+'_Mirror',(mx-.10,s*(W*.5+.13),mz+.02),(.23,.21,.12),'Body',.05)
  box(kind+'_MirrorGlass',(mx-.213,s*(W*.5+.13),mz+.02),(.014,.16,.078),'Glass',.02)
  # Real recessed lamp housings with separate low beam and DRL lenses.
  z=H*.73
  lamp=[(L*.5+.006,s*W*.19,z),(L*.5,s*W*.28,z),(L*.5-.07,s*W*.37,z-.012),(L*.5-.18,s*W*.43,z-.035)]
  pipe(kind+'_HeadHousing',lamp,.072,'Trim',10)
  pipe(kind+'_LowBeam',[(x+.067,y,zz-.018) for x,y,zz in lamp[:-1]],.029,'Headlamp',10)
  pipe(kind+'_DRL',[(x+.062,y,zz+.041) for x,y,zz in lamp],.012,'DRL',8)
  box(kind+'_TailHousing',(-L*.5-.010,s*W*.29,H*.69),(.055,.47,.15),'Trim',.055)
  box(kind+'_TailLens',(-L*.5-.041,s*W*.29,H*.70),(.027,.40,.062),'Tail',.025)
  box(kind+'_RearReflector',(-L*.49,s*W*.30,.40),(.035,.16,.035),'Tail',.015)
  box(kind+'_SideMarker',(L*.43,s*W*.45,H*.70),(.11,.026,.035),'Amber',.013)
 box(kind+'_LowerGrille',(L*.5+.015,0,.48),(.04,1.12,.16),'Trim',.05)
 for z in [.442,.48,.518]:box(kind+'_GrilleBar',(L*.5+.038,0,z),(.018,.98,.009),'Alloy',.003)
 box(kind+'_FrontPlate',(L*.5+.042,0,.62),(.023,.33,.095),'Alloy',.016)
 box(kind+'_RearPlate',(-L*.5-.025,0,.53),(.025,.33,.10),'Alloy',.016)
 box(kind+'_Chassis',(0,0,.27),(L*.72,W*.71,.09),'Trim',.035)
 # Dark seals along the window belt underline the inset cabin.
 for s in [-1,1]:
  ps=[(c[0],s*c[1],base+.07) for c in ctrl[1:-1]];pipe(kind+'_WindowSeal',ps,.012,'Trim',6)
 return list(parts),dict(length=L,width=W,height=max(c[2] for c in ctrl),wheel_radius=wr)

route=bpy.data.images.load(str(OLD/'T_AP16_TrafficPath.exr'));px=list(route.pixels)
def frame(t):
 q=(t%1)*2048;i=int(q);f=q-i;a=px[(i%2048)*4:(i%2048)*4+4];b=px[((i+1)%2048)*4:((i+1)%2048)*4+4]
 v=[a[k]*(1-f)+b[k]*f for k in range(4)];p=Vector((v[0],v[1],-105.70));d=Vector((v[2],v[3],0)).normalized()
 return p,d,Vector((-d.y,d.x,0))

def collect(objects):
 data=dict(v=[],f=[],r=[],uv=[],smooth=[],normals=[])
 for o in objects:
  activate(o)
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  # Project each final triangle, rather than a boolean n-gon whose first three
  # corners may be collinear. This keeps UV0's tangent basis non-degenerate.
  triangulate=o.modifiers.new('Surface UV topology','TRIANGULATE')
  if hasattr(triangulate,'keep_custom_normals'):triangulate.keep_custom_normals=True
  bpy.ops.object.modifier_apply(modifier=triangulate.name)
  # Material UV0 is planar in local metres; UV1 below is reserved for motion.
  me=o.data;off=len(data['v']);data['v'] += [tuple(o.matrix_world@v.co) for v in me.vertices];nm=o.matrix_world.to_3x3().inverted().transposed()
  for poly in me.polygons:
   ids=list(poly.vertices);vs=[Vector(data['v'][off+i]) for i in ids];n=(vs[1]-vs[0]).cross(vs[2]-vs[0]);axis=max(range(3),key=lambda k:abs(n[k]));xy=[k for k in range(3) if k!=axis]
   data['f'].append([off+i for i in ids]);data['r'].append(me.materials[poly.material_index].name);data['uv'].append([(v[xy[0]],v[xy[1]]) for v in vs]);data['smooth'].append(poly.use_smooth)
   data['normals'].append([tuple((nm@me.corner_normals[li].vector).normalized()) for li in poly.loop_indices])
 return data

records=[];pool=dict(v=[],f=[],r=[],uv=[],phase=[],smooth=[],normals=[])
export=R/'Meshes';export.mkdir(exist_ok=True)
def export_batch(name,d):
 # The original traffic contract stores kilometre-scale world coordinates.
 # Float32 placement can collapse tiny boolean slivers; omit only those
 # collapsed/negligible triangles before FBX creates invalid tangent wedges.
 keep=[]
 for i,face in enumerate(d['f']):
  a,b,c=[Vector(d['v'][j]) for j in face[:3]]
  if (b-a).cross(c-a).length>2e-7:keep.append(i)
 removed=len(d['f'])-len(keep)
 for key in ['f','r','uv','phase','smooth','normals']:d[key]=[d[key][i] for i in keep]
 used=sorted({j for face in d['f'] for j in face});remap={v:i for i,v in enumerate(used)}
 d['v']=[d['v'][i] for i in used];d['f']=[[remap[i] for i in face] for face in d['f']]
 # A collapsed sliver can leave a valid but edge-on weighted corner normal.
 # Limit correction to those corners; retain panel normals everywhere else.
 for face,ns in zip(d['f'],d['normals']):
  a,b,c=[Vector(d['v'][j]) for j in face[:3]];fn=-(b-a).cross(c-a).normalized()
  for j,n in enumerate(ns):
   if Vector(n).dot(fn)<.20:ns[j]=tuple(fn)
 # Reflect Y and reverse winding explicitly so custom panel normals survive.
 me=bpy.data.meshes.new(name);me.from_pydata(d['v'],[],[list(reversed(f)) for f in d['f']]);me.update()
 o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
 order=list(dict.fromkeys(d['r']))
 for r in order:me.materials.append(mats[r])
 uv=me.uv_layers.new(name='SurfaceUV');ph=me.uv_layers.new(name='TrafficPhase')
 for p,r,coords,phase,sm in zip(me.polygons,d['r'],d['uv'],d['phase'],d['smooth']):
  p.material_index=order.index(r);p.use_smooth=sm
  for li,co in zip(p.loop_indices,reversed(coords)):uv.data[li].uv=co;ph.data[li].uv=(phase,0)
 me.normals_split_custom_set([n for ns in d['normals'] for n in reversed(ns)])
 activate(o);tri=o.modifiers.new('ExportTriangles','TRIANGULATE')
 if hasattr(tri,'keep_custom_normals'):tri.keep_custom_normals=True
 bpy.ops.object.modifier_apply(modifier=tri.name)
 me=o.data;me.uv_layers.active_index=0;me.uv_layers['SurfaceUV'].active_render=True
 me.calc_tangents(uvmap='SurfaceUV')
 broken={i for i,loop in enumerate(me.loops) if loop.tangent.length<.01}
 if broken:
  normals=[tuple(n.vector) for n in me.corner_normals]
  for p in me.polygons:
   if any(i in broken for i in p.loop_indices):
    for i in p.loop_indices:normals[i]=tuple(p.normal)
  me.normals_split_custom_set(normals)
 file=export/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 return dict(name=name,fbx=str(file),triangles=len(o.data.polygons),materials=order,collapsed_submillimetre_triangles_removed=removed)

for k,kind in enumerate(['Coupe','Shuttle','Freight']):
 objects,dimensions=make(kind);src=collect(objects);d=dict(v=[],f=[],r=[],uv=[],phase=[],smooth=[],normals=[])
 for j in range(12):
  phase=(j*3+k)/36;p,f,l=frame(phase);off=len(d['v'])
  for x,y,z in src['v']:
   q=p+f*x*1.25+l*y*1.25+Vector((0,0,z*1.25));d['v'].append((q.x,-q.y,q.z))
  d['f'] += [[i+off for i in face] for face in src['f']];d['r']+=src['r'];d['uv']+=src['uv'];d['phase'] += [phase]*len(src['f']);d['smooth']+=src['smooth']
  for ns in src['normals']:
   rotated=[]
   for x,y,z in ns:
    n=f*x+l*y+Vector((0,0,z));rotated.append((n.x,-n.y,n.z))
   d['normals'].append(rotated)
  # Two soft road pools, just above the road markings. No per-car light actors.
  for side in [-1,1]:
   front=dimensions['length']*.5+.20;offp=len(pool['v'])
   for x,y in [(front,side*.55-.18),(front+8,side*.55-1.6),(front+8,side*.55+1.6),(front,side*.55+.18)]:
    q=p+f*x*1.25+l*y*1.25+Vector((0,0,.075));pool['v'].append((q.x,-q.y,q.z))
   pool['f'].append([offp+i for i in range(4)]);pool['r'].append('Pool');pool['uv'].append([(0,0),(1,0),(1,1),(0,1)]);pool['phase'].append(phase);pool['smooth'].append(False)
   pool['normals'].append([(0,0,1)]*4)
 row=export_batch('SM_CT_'+kind,d);row.update(kind=kind,count=12,dimensions_m=dimensions);records.append(row)
 # Keep editable unbatched prototypes in a hidden collection in the source blend.
 col=bpy.data.collections.new('Source_'+kind);scene.collection.children.link(col)
 for o in objects:
  for c in list(o.users_collection):c.objects.unlink(o)
  col.objects.link(o)
 col.hide_render=True;col.hide_viewport=True
records.append(dict(export_batch('SM_CT_HeadlightPools',pool),kind='HeadlightPools',count=36))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Traffic_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,cars=36,route_source=str(OLD/'T_AP16_TrafficPath.exr'),route_length_m=json.loads((OLD/'assembly.json').read_text(encoding='utf8'))['route_length_m'],uv_contract='UV0 metre surfaces, UV1.x phase (j*3+kind)/36',additional_dynamic_lights=0),indent=2),encoding='utf8')
print('TRAFFIC_GEOMETRY_EXPORTED',[(r['kind'],r['triangles']) for r in records],flush=True)
