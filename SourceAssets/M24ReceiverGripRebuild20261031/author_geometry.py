import bpy,bmesh,json,gzip,math,copy
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;S=O.parent;D=json.load(gzip.open(O/'Inputs/geometry.json.gz','rt'))
(O/'Exports').mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
T=Matrix.Translation((0,.027,.078))@Matrix.Rotation(math.pi,4,'Z')
K=Matrix.Diagonal((1,-1,1,1));Q=Matrix.Translation((0,.027,.078))@Matrix.Diagonal((-1,1,1,1))
report={'grip_source_to_m24':list(map(list,T)),'m4_root_ue_to_m24_points':list(map(list,Q)),'exports':{},'materials':{},'native_rear_seat_faces':[]}
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color,metal,rough):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
coat=mat('M24_NewReceiverMetal',(.028,.031,.034),1,.38);rubber=mat('M24_NewPistolGrip',(.017,.019,.019),0,.55)
def geometry(name,v,f,material):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material);return ob
def normals_uv(ob,bevel=0):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
 bpy.context.view_layer.objects.active=ob
 if bevel:
  m=ob.modifiers.new('Manufactured edge radius','BEVEL');m.width=bevel;m.segments=3;m.limit_method='ANGLE';m.angle_limit=.5;bpy.ops.object.modifier_apply(modifier=m.name)
 for p in ob.data.polygons:p.use_smooth=True
 m=ob.modifiers.new('Planar corner normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
 if not ob.data.uv_layers:
  uv=ob.data.uv_layers.new(name='MetricUV')
  for p in ob.data.polygons:
   a=sorted(range(3),key=lambda k:abs(p.normal[k]))[:2]
   for li in p.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v[a[0]]*20,v[a[1]]*20)
def export(name,obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
 path=O/'Exports'/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,use_triangles=True)
 report['exports'][name]=str(path)
def loops(edges):
 edges=list(edges);result=[]
 while edges:
  a,b=edges.pop();ring=[a,b]
  while ring[-1]!=ring[0]:
   found=next((i for i,e in enumerate(edges) if ring[-1] in e),None)
   if found is None:raise RuntimeError('Open authored mating ring')
   a,b=edges.pop(found);ring.append(b if a==ring[-1] else a)
  result.append(ring[:-1])
 return result
def cut_top(ob,z):
 # Only the mounting neck is recut. The actual pistol-grip body and UVs remain.
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,z),plane_no=(0,0,1),dist=.0000001,clear_outer=True)
 cap=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
 for f in cap:
  for uv in bm.loops.layers.uv.values():
   for l in f.loops:l[uv].uv=(l.vert.co.x*20,l.vert.co.y*20)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
 # Exported source normals are regenerated after the local neck operation.
 for p in ob.data.polygons:p.use_smooth=True
 bpy.context.view_layer.objects.active=ob;m=ob.modifiers.new('Grip neck normal weighting','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
grips=[]
m4=D['M4'];v=np.array(m4['positions']);f=np.array(m4['triangles']);mi=np.array(m4['material_ids']);root=Matrix(m4['bones']['WPN_root']['world'])
slot=next(i for i,m in enumerate(m4['materials']) if m['slot'].startswith('Grip_Default'))
ids=np.unique(f[mi==slot]);remap={int(v):i for i,v in enumerate(ids)}
points=[list(Q@root.inverted()@Vector(v[i])) for i in ids]
native=geometry('M24_PistolGrip_Default',points,[[remap[int(i)] for i in tri] for tri in f[mi==slot]],rubber);normals_uv(native);cut_top(native,.084);grips.append(native)
report['materials']['M24_NewPistolGrip']='/Game/Weapons/SkeletonSniperStock20261031/M24Direct20261031/Materials/MI_M24_IndependentGrip'
export('SM_M24_PistolGrip_Default',[native]);native.hide_set(True)
for key in ('balanced','phantom','stable'):
 before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')));obs=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
 for ob in obs:
  ob.data.transform(T@ob.matrix_world);ob.matrix_world=Matrix.Identity(4);ob.parent=None;ob.name='M24_PistolGrip_'+key
  for i,slot in enumerate(ob.data.materials):
   source=D[key]['materials'][i];unique='M24_Grip_'+key+'_'+str(i);slot.name=unique;report['materials'][unique]=source['asset']
  cut_top(ob,.084)
 export('SM_M24_PistolGrip_'+key,obs);grips+=obs
 for ob in obs:ob.hide_set(True)
neck_points=[v.co.copy() for ob in grips for v in ob.data.vertices if abs(v.co.z-.084)<.00001]
report['grip_neck_bounds']=[[min(p[k] for p in neck_points) for k in range(3)],[max(p[k] for p in neck_points) for k in range(3)]]
# Repartition only the polymer fore-end behind its first intact receiver ring.
# Identification uses connected native faces, not a box selection of the gun.
h=D['M24'];hv=np.array(h['positions'])*[.01,-.01,.01];hf=np.array(h['triangles']);hm=np.array(h['material_ids']);parent={}
def find(p):
 parent.setdefault(p,p)
 while parent[p]!=p:parent[p]=parent[parent[p]];p=parent[p]
 return p
def join(a,b):parent[find(a)]=find(b)
keys=[tuple(np.round(p,6)) for p in hv]
for tri,ma in zip(hf,hm):
 if ma in (4,5,6):join(keys[tri[0]],keys[tri[1]]);join(keys[tri[1]],keys[tri[2]])
wrist_roots={find(keys[int(i)]) for tri,ma in zip(hf,hm) if ma==4 for i in tri}
selected={i for i,(tri,ma) in enumerate(zip(hf,hm)) if ma==5 and find(keys[int(tri[0])]) in wrist_roots and hv[tri,1].min()<.100}
centers=[(hv[hf[i]].mean(0)*[100,-100,100]).tolist() for i in sorted(selected)]
(O/'Inputs/native_rear_seat_faces.json').write_text(json.dumps(centers));report['native_rear_seat_faces']=len(centers)
edges={}
for i,(tri,ma) in enumerate(zip(hf,hm)):
 if ma!=5:continue
 for a,b in zip(tri,np.roll(tri,-1)):
  edge=tuple(sorted((keys[a],keys[b])));edges.setdefault(edge,[]).append(i in selected)
boundary=loops([e for e,marks in edges.items() if any(marks) and not all(marks)])
report['native_boundary_loops']=boundary
native_adapters=[]
for j,ring in enumerate(boundary):
 if len(ring)<4:continue
 # Match the real, non-planar host cut exactly; the rear ring meets the new core.
 c=np.array(ring).mean(0);rear=[]
 for p in ring:
  a=math.atan2(p[2]-c[2],p[0]-c[0]);cs,sn=math.cos(a),math.sin(a)
  rear.append((.024*math.copysign(abs(cs)**.5,cs),.079,.081+.026*math.copysign(abs(sn)**.5,sn)))
 n=len(ring);faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 ob=geometry('Native_receiver_exact_seat_'+str(j),ring+rear,faces,coat);normals_uv(ob,.00025);native_adapters.append(ob)
# Sculpted receiver bridge, with an independent flat-bottom grip mounting seat.
seat_rear=min(-.012,min(p.y for p in neck_points)-.0004)
seat_front=max(.054,max(p.y for p in neck_points)+.0004)
profile=[(.080,.055),(.070,.060),(seat_front,.084),(seat_rear,.084),(-.042,.070),(-.042,.054),(-.042,.108),(.080,.107)]
n=len(profile);vs=[(sign*(.011 if y<-.034 else .024),y,z) for sign in (-1,1) for y,z in profile]
fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
core=geometry('M24_NewReceiverAndGripSeat',vs,fs,coat)
normals_uv(core,.00055)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.012,depth=.165,location=(0,.027,.114),rotation=(math.pi/2,0,0));tool=bpy.context.object
bpy.context.view_layer.objects.active=core;mod=core.modifiers.new('Bolt clearance groove','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
with bpy.data.libraries.load(str(S/'SkeletonSniperStock20261031/SkeletonSniperStock_M24_Editable.blend'),link=False) as (src,dst):dst.objects=['SniperSkeleton_M24']
stock=dst.objects[0];bpy.context.collection.objects.link(stock)
old_front=Vector((0,-.125,.039));old_back=Vector((0,-.3603858947753906,.029875358566641808));front=Vector((0,-.04,.081));back=Vector((0,-.3603858947753906,.045))
scale=(back-front).length/(old_back-old_front).length;rot=(old_back-old_front).rotation_difference(back-front)
stock.data.transform(Matrix.Translation(front)@rot.to_matrix().to_4x4()@Matrix.Scale(scale,4)@Matrix.Translation(-old_front));stock.name='M24_SkeletonStock_ReferenceProportion'
for im in bpy.data.images:
 if im.source=='FILE' and im.filepath:im.filepath=bpy.path.abspath(im.filepath)
report['materials']['SniperStock_MeshySurface']='/Game/Weapons/SkeletonSniperStock20261031/Materials/MI_SniperStock_MeshySurface'
report['materials']['M24_NewReceiverMetal']='/Game/Weapons/M24/ReceiverGripRebuild20261031/Materials/MI_M24_ReceiverSeat'
report['stock_scale_from_first_fit']=scale;report['stock_hinge_front']=list(front);report['stock_shoulder_target']=list(back)
export('SM_M24_ReceiverStock_Native',[stock,core]+native_adapters)
# The advanced chassis has its own measured cut. Remove its old wrist adaptor,
# retain the trigger guard/upper receiver, and shorten only the rear lower walls.
before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/advanced.fbx'));advanced=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');advanced.data.transform(advanced.matrix_world);advanced.matrix_world=Matrix.Identity(4)
for i,m in enumerate(advanced.data.materials):m.name='M24_Advanced_'+str(i);report['materials'][m.name]=D['advanced']['materials'][i]['asset']
bm=bmesh.new();bm.from_mesh(advanced.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00003)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00003)
components=[];seen=set()
for start in bm.verts:
 if start in seen:continue
 todo=[start];group=set();seen.add(start)
 while todo:
  v=todo.pop();group.add(v)
  for e in v.link_edges:
   other=e.other_vert(v)
   if other not in seen:seen.add(other);todo.append(other)
 components.append(group)
advanced_cuts=[]
for group in components:
 lo=Vector([min(v.co[k] for v in group) for k in range(3)]);hi=Vector([max(v.co[k] for v in group) for k in range(3)])
 if lo.y>=.111 or hi.z>.110:continue
 # The separate trigger-guard shell extends below 4.4 cm and has a long span.
 if lo.z<.044 and hi.y>.14:continue
 faces={f for v in group for f in v.link_faces};edges={e for v in group for e in v.link_edges}
 if hi.y<.112:
  bmesh.ops.delete(bm,geom=list(group),context='VERTS');continue
 result=bmesh.ops.bisect_plane(bm,geom=list(group)+list(edges)+list(faces),plane_co=(0,.11237,0),plane_no=(0,1,0),dist=.0000001,clear_inner=True)
 cut_vertices=[v for v in bm.verts if abs(v.co.y-.11237)<.000001]
 bmesh.ops.remove_doubles(bm,verts=cut_vertices,dist=.00003)
 cut_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-.11237)<.000001 for v in e.verts)]
 if cut_edges:
  raw_edges=list(set(tuple(sorted(tuple(round(a,6) for a in v.co) for v in e.verts)) for e in cut_edges))
  (O/'Inputs/advanced_cut_edges.json').write_text(json.dumps(raw_edges))
  cut_loops=loops(raw_edges);advanced_cuts+=cut_loops
  cap=bmesh.ops.holes_fill(bm,edges=cut_edges,sides=0)['faces']
  for f in cap:
   for uv in bm.loops.layers.uv.values():
    for l in f.loops:l[uv].uv=(l.vert.co.x*20,l.vert.co.z*20)
bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(advanced.data);bm.free()
advanced.name='M24_AdvancedFront_ForIndependentGrip';export('SM_M24_AdvancedFront_ForIndependentGrip',[advanced])
advanced_adapters=[]
for j,ring in enumerate(advanced_cuts):
 # Copy each real side-wall section; close it into the core rather than using
 # a guessed central box that leaves a visible outline mismatch.
 rear=[(max(-.024,min(.024,p[0])),.079,max(.055,min(.107,p[2]))) for p in ring];n=len(ring)
 fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 ob=geometry('Advanced_receiver_exact_seat_'+str(j),ring+rear,fs,coat);normals_uv(ob,.0002);advanced_adapters.append(ob)
export('SM_M24_ReceiverStock_Advanced',[stock,core]+advanced_adapters)
report['advanced_boundary_loops']=advanced_cuts
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_set(ob not in [stock,core,advanced,native]+advanced_adapters);ob.hide_render=ob not in [stock,core,advanced,native]+advanced_adapters
native.hide_set(False);native.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReceiverGrip_Editable.blend'))
(O/'geometry_contract.json').write_text(json.dumps(report,indent=2));print('M24_NEW_GEOMETRY_AUTHORED',list(report['exports']),flush=True)
