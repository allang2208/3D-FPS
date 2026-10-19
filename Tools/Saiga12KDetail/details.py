"""Authored geometric detail in the existing seated centimetre frame.
Executed inside author.py before its final join, UV layout and export.
"""
from mathutils import Matrix

def remove(ob):
 objects.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)

def bezier(points,steps=32):
 p=np.array(points);return [(1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3] for t in np.linspace(0,1,steps)]

def strip(name,path,width,thickness,part,cx=.08):
 # Solid rectangular strip with radiused edges, not a wire/tube guard.
 p=np.array(path);vs=[];fs=[]
 for i,v in enumerate(p):
  t=p[min(i+1,len(p)-1)]-p[max(0,i-1)];t/=np.linalg.norm(t);normal=np.array([-t[1],t[0]])*thickness/2
  for x,d in [(-width/2,-1),(width/2,-1),(width/2,1),(-width/2,1)]:
   y,z=v+normal*d;vs.append([cx+x,y,z])
 for i in range(len(p)-1):
  for j in range(4):k=(j+1)%4;fs.append([i*4+j,i*4+k,(i+1)*4+k,(i+1)*4+j])
 fs.extend([[3,2,1,0],list(range((len(p)-1)*4,len(p)*4))])
 return clean(mesh(name,vs,fs,[part]*len(fs)),.035,3,False)

# Replace only the clearly angular guard/trigger, retaining the native anchors.
remove(next(o for o in objects if o.name=='Native body 07'))
path=bezier([(-.92,1.03),(-.95,-1.6),(-1.0,-2.55),(.35,-2.55)],24)
path+=bezier([(.35,-2.55),(1.4,-2.55),(2.8,-2.55),(3.45,-2.48)],18)[1:]
path+=bezier([(3.45,-2.48),(4.55,-2.4),(4.4,-.3),(4.38,1.03)],24)[1:]
strip('Radiused stamped trigger guard',path,.72,.18,'Body')
remove(next(o for o in objects if o.name=='Native Trigger'))
strip('Continuous curved trigger',bezier([(-.38,.95),(-.55,-.60),(.25,-1.76),(1.92,-1.85)],42),.57,.19,'Trigger')

def projected_rib(ob,name,yz,side,radius,part,offset=.006):
 tr=tree(ob);pts=[];norm=[]
 for y,z in yz:
  hit,no,_,_=tr.ray_cast(Vector((side*8,-float(y),float(z))),Vector((-side,0,0)),16)
  if hit is not None and no.x*side>.30:pts.append(hit+no*offset);norm.append(no)
 if len(pts)<3:return
 # Flat topped molded lands. Their broad faces avoid the beaded/wire appearance
 # of the first draft while the rounded shoulders catch a narrow highlight.
 vs=[];fs=[];n=8
 profile=[(-1,-.08),(-1,.10),(-.8,.30),(.8,.30),(1,.10),(1,-.08),(.8,-.20),(-.8,-.20)]
 for i,(p,no) in enumerate(zip(pts,norm)):
  tangent=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized();across=tangent.cross(no).normalized();up=across.cross(tangent).normalized();taper=.6 if i in (0,len(pts)-1) else 1.
  for a,b in profile:
   v=p+across*(a*radius*taper)+up*(b*radius);vs.append([v.x,-v.y,v.z])
 for i in range(len(pts)-1):
  for j in range(n):k=(j+1)%n;fs.append([i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j])
 fs.extend([list(range(n-1,-1,-1)),list(range((len(pts)-1)*n,len(pts)*n))]);clean(mesh(name,vs,fs,[part]*len(fs)),0,3,False)

def ring_x(name,x,y,z,ry,rz,thickness,part,side=1):
 vs=[];fs=[];n=40
 for xx,s in [(x,1),(x+side*.025,1),(x+side*.025,1-thickness),(x,1-thickness)]:
  for a in np.linspace(0,2*math.pi,n,endpoint=False):vs.append([xx,y+ry*s*math.cos(a),z+rz*s*math.sin(a)])
 for i in range(4):
  for j in range(n):k=(j+1)%n;fs.append([i*n+j,i*n+k,((i+1)%4)*n+k,((i+1)%4)*n+j])
 return clean(mesh(name,vs,fs,[part]*len(fs)),0,3,False)

# Native receiver rivets retain their positions; add subtle pressed seats around them.
for i in sorted(pin_ids):
 lo,hi=np.array(body[i]['bounds']);mid=(lo+hi)/2;ry=(hi[1]-lo[1])/2;rz=(hi[2]-lo[2])/2
 if max(ry,rz)>.55:continue
 for side,x in [(-1,lo[0]),(1,hi[0])]:
  if abs(x-.08)>.9:ring_x('Pressed receiver rivet seat',x-side*.015,mid[1],mid[2],ry*1.18,rz*1.18,.15,'Body',side)

hg=next(o for o in objects if o.name=='Native Handguard')
for side in (-1,1):
 # Recesses are shallow molded details with floors; no invented open receiver holes.
 for y in np.linspace(26.0,34.6,6):
  projected_rib(hg,'Handguard inset diagonal grip land',[(y+(z-3.65)*.48,z) for z in np.linspace(2.88,4.4,18)],side,.14,'Handguard',.01)
 projected_rib(hg,'Handguard mold shoulder line',[(y,5.65) for y in np.linspace(23.8,36.5,70)],side,.026,'Handguard')

# Grip lines now have tapered round ends and a deliberate chevron layout.
for ob in list(objects):
 if ob.name.startswith('Molded rear grip flute'):remove(ob)
for side in (-1,1):
 for z in np.linspace(-2.8,-7.35,8):
  projected_rib(grip,'Rear grip chevron traction',[(y,z-.2*abs(y+4.4)) for y in np.linspace(-5.9,-2.8,30)],side,.10,'RearGrip')
 projected_rib(grip,'Grip inset rear border',[(-6.0,z) for z in np.linspace(-3.0,-7.3,38)],side,.035,'RearGrip')

# Intentional contact serrations on the existing moving charging handle.
bolt=next(o for o in objects if o.name=='Native Bolt')
bp=np.array([[v.co.x,-v.co.y,v.co.z] for v in bolt.data.vertices]);end=bp[bp[:,0]<-2.7]
if len(end):
 ymn,ymx=end[:,1].min(),end[:,1].max();zmn,zmx=end[:,2].min(),end[:,2].max()
 for y in np.linspace(ymn+.10,ymx-.10,6):projected_rib(bolt,'Charging handle contact serration',[(y,z) for z in np.linspace(zmn+.10,zmx-.10,18)],-1,.033,'Bolt')
safety=next(o for o in objects if o.name=='Native Safety')
for y in np.linspace(5.9,7.6,6):projected_rib(safety,'Selector thumb pad serration',[(y,z) for z in np.linspace(2.40,2.69,9)],-1,.026,'Safety')

# A thin rolled edge around the source receiver's open action reinforces its depth.
for side in (-1,1):
 shell=next(o for o in objects if o.name=='Native body 04')
 projected_rib(shell,'Receiver lower folded seam',[(y,.70) for y in np.linspace(-7.7,17.6,95)],side,.028,'Body')

def label(text,host,y,z,size,side,part='LaserMark'):
 # Project shallow geometry onto the actual part. Text follows the view-facing side.
 tr=tree(host);hit,no,_,_=tr.ray_cast(Vector((side*8,-y,z)),Vector((-side,0,0)),16)
 if hit is None:return
 cu=bpy.data.curves.new('Shallow identification '+text,'FONT');cu.body=text;cu.size=size;cu.space_character=1.10;cu.align_x='CENTER';cu.align_y='CENTER';cu.resolution_u=3;cu.extrude=0;cu.bevel_depth=0
 ob=bpy.data.objects.new(cu.name,cu);scene.collection.objects.link(ob)
 # Local X is horizontal, local Y vertical, local Z points out of the receiver.
 xx=Vector((0,side,0));yy=Vector((0,0,1));zz=Vector((side,0,0));ob.matrix_world=Matrix(((xx.x,yy.x,zz.x,0),(xx.y,yy.y,zz.y,0),(xx.z,yy.z,zz.z,0),(0,0,0,1)));ob.location=hit+no*.005
 select(ob);bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 # Conform every glyph to the underlying surface; avoid any floating label planes.
 for v in ob.data.vertices:
  h,n,_,_=tr.ray_cast(Vector((side*8,v.co.y,v.co.z)),Vector((-side,0,0)),16)
  if h is not None:v.co.x=h.x+side*.006
 ob.data.materials.append(material(part));objects.append(ob)

receiver=next(o for o in objects if o.name=='Native body 04')
label('12K',receiver,10.6,2.85,.53,1)
label('12 GA',receiver,10.6,1.85,.30,1)
label('S',receiver,7.8,4.15,.32,-1)
label('F',receiver,8.6,2.2,.32,-1)

def magazine_detail(ob,part,low):
 if part=='ExtMagazine':
  # Round only the heavy lip and floorplate edges; broad curved walls stay intact.
  me=ob.data;bm=bmesh.new();bm.from_mesh(me);bm.edges.ensure_lookup_table()
  selected={e.index for e in bm.edges if e.is_manifold and e.calc_face_angle()>.6 and e.calc_length()>.12 and all(v.co.z>-.8 or v.co.z<low+.2 for v in e.verts)};bm.free()
  weights=me.attributes.new('bevel_weight_edge','FLOAT','EDGE')
  for i,w in enumerate(weights.data):w.value=1. if i in selected else 0.
  select(ob);mod=ob.modifiers.new('Selective molded lip radii','BEVEL');mod.limit_method='WEIGHT';mod.width=.018;mod.segments=3;mod.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=mod.name);clean(ob,0,3,False)
 # Cross ribs follow the real curved side, seated throat and floorplate stay unchanged.
 for side in (-1,1):
  for z in np.arange(-4.4,low+1.3,-1.25):
   y=50.628671656-math.sqrt(max(38.165166013**2-(z-4.76056238)**2,1.))
   projected_rib(ob,part+' transverse molded grip land',[(yy,z) for yy in np.linspace(y-2.6,y+2.6,32)],side,.12,part,.01)
  # Longitudinal narrow recessed-panel edge is retained from the original pass.
 # Subtle molded capacity stamp is integral polymer and hides with the magazine.
  z=low+.8;y=50.628671656-math.sqrt(max(38.165166013**2-(z-4.76056238)**2,1.))
  label('12' if part=='ExtMagazine' else '8',ob,y,z,.45,side,part)
magazine_detail(next(o for o in objects if o.name=='Native Magazine'),'Magazine',-11.8)

(O/'Receipts/detail-design.json').write_text(json.dumps({'new_details':['radiused sheet trigger guard','continuous curved trigger','pressed receiver pin seats','molded handguard lands and shoulder line','chevron grip traction','charging handle and selector serrations','receiver folded seam','subtle 12K / 12 GA and selector markings','curved magazine transverse grip lands and capacity stamp'],'universal_grain':False,'new_root_slot':'Saiga12K_LaserMark','moving_detail_slots':'Bolt, Trigger, Magazine; existing mechanical bones','factory_visibility':'No new slots for stock/grip/magazine details'},indent=2))
