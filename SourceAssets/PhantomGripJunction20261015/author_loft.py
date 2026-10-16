"""Join the retained phantom body to the host's real factory mounting surface."""
import bpy,bmesh,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());CFG=json.loads((O/'sections.json').read_text());OUT=O/'Exports';OUT.mkdir(exist_ok=True);key=sys.argv[sys.argv.index('--')+1];cfg=CFG[key];row=D['assets'][key];cut=cfg['cut'];top=cfg['high'];body_slot=cfg['body_slot'];native_slot={'M4':1,'AKM':1,'QBZ191':1,'M16':0,'PKM':0,'HK416':1,'A762':3}[key]
# Start below the old head's recessed decoration, on a complete convex section.
# Cutting through that recess would stretch its rim into folds in the new neck.
cut,top={'M4':(-.002,.014),'M16':(-.002,.011),'AKM':(-.014,.005),'QBZ191':(0.,.017),'PKM':(-.008,.017),'HK416':(-.001,.003),'A762':(-.0115,-.006)}[key]
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.import_scene.fbx(filepath=row['fbx']);body=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=body.data
nm=body.matrix_world.to_3x3().inverted().transposed();norm=[tuple((nm@n.vector).normalized()) for n in me.corner_normals];me.transform(body.matrix_world);body.parent=None;body.matrix_world=Matrix.Identity(4);me.normals_split_custom_set(norm)
HK=Matrix(json.loads((O.parent/'HK416Reworked20260930/authoring.json').read_text())['root_matrix'])
if key=='HK416':me.transform(HK.inverted())
materials=[]
for i,s in enumerate(row['slots']):materials.append(bpy.data.materials.new(s['name']))
saved_mids=[f.material_index for f in me.polygons];me.materials.clear()
for m in materials:me.materials.append(m)
for f,i in zip(me.polygons,saved_mids):f.material_index=i
uvnames=[u.name for u in me.uv_layers];color_names=[(a.name,a.data_type,a.domain) for a in me.color_attributes]
existing_upper=None
if key in ['HK416','A762','PKM']:
 existing_upper=body.copy();existing_upper.data=me.copy();bpy.context.collection.objects.link(existing_upper)
def mark(ob,region):
 me=ob.data;na=me.attributes.new('JoinCornerNormal','FLOAT_VECTOR','CORNER');na.data.foreach_set('vector',np.asarray([tuple(n.vector) for n in me.corner_normals],dtype=np.float32).ravel());ra=me.attributes.new('JoinRegion','INT','FACE')
 for d in ra.data:d.value=region
def clip(ob,z,upper,slot=None):
 bm=bmesh.new();bm.from_mesh(ob.data)
 if slot is not None:bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=slot],context='FACES')
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
 bm.to_mesh(ob.data);bm.free()
mark(body,0);clip(body,cut,False,body_slot)
with (O/'Input'/(key+'_host.bin')).open('rb') as f:
 h=json.loads(f.readline());p=np.fromfile(f,'<f4',h['vertices']*3).reshape(-1,3)*[.01,-.01,.01];t=np.fromfile(f,'<i4',h['triangles']*3).reshape(-1,3);m=np.fromfile(f,'<i4',h['triangles']);n=np.fromfile(f,'<f4',h['triangles']*9).reshape(-1,3,3)*[1,-1,1]
ids=np.flatnonzero(np.isin(m,h['factory_slots']));um=bpy.data.meshes.new('Native mounting face');um.from_pydata(p,[],t[ids]);um.update()
for mat in materials:um.materials.append(mat)
for face in um.polygons:face.material_index=native_slot;face.use_smooth=True
um.normals_split_custom_set(n[ids].reshape(-1,3).tolist());upper=bpy.data.objects.new('Original host mounting surface',um);bpy.context.collection.objects.link(upper)
for name in uvnames:
 uv=um.uv_layers.new(name=name)
 for f in um.polygons:
  axis=max(range(3),key=lambda j:abs(f.normal[j]));axes=[j for j in range(3) if j!=axis]
  for li in f.loop_indices:
   co=um.vertices[um.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/.04,co[axes[1]]/.04)
for name,typ,domain in color_names:
 col=um.color_attributes.new(name=name,type=typ,domain=domain)
 for d in col.data:d.color=(1,1,1,1)
mark(upper,1);clip(upper,top,True)
if existing_upper:
 bpy.data.objects.remove(upper,do_unlink=True);upper=existing_upper
 mark(upper,1);bm=bmesh.new();bm.from_mesh(upper.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==body_slot],context='FACES');bm.to_mesh(upper.data);bm.free();clip(upper,top,True)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);upper.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join();me=body.data
bm=bmesh.new();bm.from_mesh(me);normal_layer=bm.loops.layers.float_vector['JoinCornerNormal'];region=bm.faces.layers.int['JoinRegion'];newfaces=[]
def planar_loops(z,allow_open=False):
 verts=[v for v in bm.verts if abs(v.co.z-z)<1e-7];bmesh.ops.remove_doubles(bm,verts=verts,dist=1e-6)
 edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-7 for v in e.verts)];adj={}
 for e in edges:
  a,b=e.verts;adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a)
 ends=[v for v,ns in adj.items() if len(ns)==1];healed=[]
 while len(ends)>1:
  a,b=min(((a,b) for i,a in enumerate(ends) for b in ends[i+1:]),key=lambda pair:(pair[0].co-pair[1].co).length)
  dist=(a.co-b.co).length
  if dist>.00015 and not (allow_open and len(ends)==2):break
  if not bm.edges.get((a,b)):bm.edges.new((a,b))
  adj[a].add(b);adj[b].add(a);ends.remove(a);ends.remove(b);healed.append(dist)
 order={v:sorted(ns,key=lambda w:math.atan2(w.co.y-v.co.y,w.co.x-v.co.x)) for v,ns in adj.items()};seen=set();loops=[]
 for start,neighbors in order.items():
  for second in neighbors:
   if (start,second) in seen:continue
   a,b=start,second;loop=[]
   while (a,b) not in seen:
    seen.add((a,b));loop.append(a);ns=order[b];c=ns[(ns.index(a)-1)%len(ns)];a,b=b,c
   if (a,b)!=(start,second) or len(loop)<3 or len(set(loop))!=len(loop):continue
   area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))*.5
   if area>1e-10:loops.append((area,loop))
 loops.sort(key=lambda p:p[0],reverse=True)
 if not loops:raise RuntimeError('No complete measured boundary '+key+' '+str(z))
 return loops,healed
lower_loops,lower_healed=planar_loops(cut);upper_loops,upper_healed=planar_loops(top,True);lower=lower_loops[0][1];upper=upper_loops[0][1]
def corner_normal(v):
 n=Vector()
 for f in v.link_faces:
  for l in f.loops:
   if l.vert==v:n+=l[normal_layer]
 return n.normalized() if n.length>1e-9 else v.normal.copy()
ln={v:corner_normal(v) for v in lower};un={v:corner_normal(v) for v in upper}
def sample(loop,normals,angle):
 center=sum((v.co for v in loop),Vector())/len(loop);d=Vector((math.cos(angle),math.sin(angle)));hits=[]
 def cross(a,b):return a.x*b.y-a.y*b.x
 for a,b in zip(loop,loop[1:]+loop[:1]):
  aa=a.co.xy-center.xy;e=b.co.xy-a.co.xy;den=cross(d,e)
  if abs(den)<1e-12:continue
  distance=cross(aa,e)/den;s=cross(aa,d)/den
  if distance>=0 and -1e-7<=s<=1.0000001:hits.append((distance,a,b,max(0,min(1,s))))
 if not hits:raise RuntimeError('Boundary not star shaped '+key)
 _,a,b,s=max(hits,key=lambda item:item[0]);p=a.co.lerp(b.co,s);normal=normals[a].lerp(normals[b],s).normalized();return p,normal
def face(verts):
 try:f=bm.faces.new(verts)
 except ValueError:return
 f[region]=2;f.material_index=native_slot;f.smooth=True;newfaces.append(f);return f
N=192;LEVELS=18;length=top-cut;source=[]
for j in range(N):
 theta=math.tau*j/N;p,np_=sample(lower,ln,theta);q,nq=sample(upper,un,theta);sec=(q-p)/length
 slopes=[]
 for normal in [np_,nq]:
  xy=normal.xy;d=max(xy.length_squared,1e-8);s=Vector((-normal.z*xy.x/d,-normal.z*xy.y/d,1))
  for a in [0,1]:
   if s[a]*sec[a]<=0:s[a]=0
   else:s[a]=math.copysign(min(abs(s[a]),abs(sec[a])*3,1.5),s[a])
  slopes.append(s)
 source.append((p,q,slopes[0],slopes[1],np_,nq))
rings=[];norms={};levels={}
for k in range(1,LEVELS):
 t_=k/LEVELS;ring=[]
 for p,q,a,b,na,nb in source:
  xyz=p*(2*t_**3-3*t_**2+1)+a*(length*(t_**3-2*t_**2+t_))+q*(-2*t_**3+3*t_**2)+b*(length*(t_**3-t_**2));v=bm.verts.new(xyz);ring.append(v);levels[v]=t_;norms[v]=(na,nb)
 rings.append(ring)
def stitch(a,b):
 ca=sum((v.co for v in a),Vector())/len(a);cb=sum((v.co for v in b),Vector())/len(b)
 angle=lambda v,c:math.atan2(v.co.y-c.y,v.co.x-c.x)%math.tau
 a=sorted(a,key=lambda v:angle(v,ca));b=sorted(b,key=lambda v:angle(v,cb));ap=[angle(v,ca) for v in a];bp=[angle(v,cb) for v in b];i=j=0
 while i<len(a) or j<len(b):
  an=ap[(i+1)%len(a)]+(math.tau if i+1>=len(a) else 0) if i<len(a) else float('inf');bn=bp[(j+1)%len(b)]+(math.tau if j+1>=len(b) else 0) if j<len(b) else float('inf')
  if an<bn:face((a[i%len(a)],a[(i+1)%len(a)],b[j%len(b)]));i+=1
  else:face((a[i%len(a)],b[(j+1)%len(b)],b[j%len(b)]));j+=1
stitch(lower,rings[0])
for a,b in zip(rings,rings[1:]):
 for j in range(N):face((a[j],a[(j+1)%N],b[(j+1)%N],b[j]))
stitch(rings[-1],upper)
# Close only nested cut shells and inherited openings in the copied mounting head.
for loops,z,slot in [(lower_loops[1:],cut,body_slot),(upper_loops[1:],top,native_slot)]:
 for _,loop in loops:
  edges=[bm.edges.get((a,b)) for a,b in zip(loop,loop[1:]+loop[:1])];edges=[e for e in edges if e and e.is_boundary]
  for f in bmesh.ops.holes_fill(bm,edges=edges,sides=0).get('faces',[]):f[region]=2;f.material_index=slot;f.smooth=True;newfaces.append(f)
native_open=[e for e in bm.edges if e.is_boundary and all(v.co.z>=top-1e-7 for v in e.verts)]
for f in bmesh.ops.holes_fill(bm,edges=native_open,sides=0).get('faces',[]):f[region]=2;f.material_index=native_slot;newfaces.append(f)
bm.normal_update();uvlayers=list(bm.loops.layers.uv.values());clayers=list(bm.loops.layers.color.values())
for f in newfaces:
 axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
 for l in f.loops:
  for layer in uvlayers:l[layer].uv=(l.vert.co[axes[0]]/.04,l.vert.co[axes[1]]/.04)
  for layer in clayers:l[layer]=(1,1,1,1)
  v=l.vert;n=v.normal.copy()
  if v in ln:n=ln[v]
  elif v in un:n=un[v]
  elif v in levels:
   t_=levels[v];na,nb=norms[v];w=max(0,1-t_*6) if t_<.5 else max(0,1-(1-t_)*6);n=n.lerp(na if t_<.5 else nb,w*.75).normalized()
  l[normal_layer]=n
bmesh.ops.triangulate(bm,faces=list(newfaces));bm.to_mesh(me);bm.free()
norms=[tuple(v.vector.normalized()) if v.vector.length>1e-9 else (0,0,1) for v in me.attributes['JoinCornerNormal'].data]
for f in me.polygons:f.use_smooth=True
me.normals_split_custom_set(norms)
if key=='HK416':me.transform(HK)
body.name=row['path'].rsplit('/',1)[1];me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
fbx=OUT/(key+'.fbx');blend=OUT/(key+'.blend');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False);bpy.ops.wm.save_as_mainfile(filepath=str(blend))
result={'fbx':str(fbx),'blend':str(blend),'triangles':len(me.polygons),'body_slot':body_slot,'cut':cut,'native_cut':top,'lower_boundary_vertices':len(lower),'upper_boundary_vertices':len(upper),'lower_loops':len(lower_loops),'native_loops':len(upper_loops),'closed_native_opening_edges_mm':[v*1000 for v in upper_healed],'shared_boundary_vertices':True,'lower_body_unchanged_below_m':cut-1e-6,'native_contact':'Copied current host factory upper surface; no scaling or offset','preserved_interface_triangles':'Native mounting surface rebuilt from current host; exact cut boundary stitched'}
if key in ['HK416','A762','PKM']:
 result['native_contact']='Existing upper mounting surface preserved; lower neck rebuilt with shared boundary vertices'
 result['preserved_interface_triangles']='Upper native mounting surface retained; only the lower transition was rebuilt'
(O/(key+'_authoring.json')).write_text(json.dumps(result,indent=2));print('JUNCTION_AUTHORED',key,result,flush=True)
