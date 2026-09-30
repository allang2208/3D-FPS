"""Rebuild each grip neck from its own cut boundary; retain lower grip attributes."""
import bpy,bmesh,json,math,heapq,os,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
S=Path(__file__).parent.parent;O=Path(os.environ.get('J44_OUTPUT',str(Path(__file__).parent)));(O/'Exports').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'GripFinish43/LMG201_GripFinish43.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];root=rig.data.bones['WPN_root'].matrix_local.copy();rig.animation_data_clear();rig.data.pose_position='REST';report={}

def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]

def localize(ob,xf):
 ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(xf);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.data.normals_split_custom_set(ns)

def bind(ob):
 ns=[(root.to_3x3()@n.vector).normalized() for n in ob.data.corner_normals];ob.data.transform(root);ob.data.normals_split_custom_set(ns);ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.vertex_groups.clear();ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1.,'REPLACE');ob.modifiers.new('Original201Rig','ARMATURE').object=rig

def reconnect_source(ob,key):
 # The imported donor consists of broken surface tiles. Reconstruct their
 # volume at submillimetre resolution, then transfer the authored corner data.
 donor=ob.copy();donor.data=ob.data.copy();bpy.context.scene.collection.objects.link(donor);donor.name='J44_RetainedDonor_'+key;donor.hide_render=True
 select([ob]);remesh=ob.modifiers.new('Rejoin broken grip tiles','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.00022;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
 if not ob.data.polygons:raise RuntimeError('No reconstructed grip '+key)
 data=ob.modifiers.new('Preserve source corner data','DATA_TRANSFER');data.object=donor;data.use_loop_data=True;data.data_types_loops={'UV','CUSTOM_NORMAL'};data.loop_mapping='POLYINTERP_NEAREST';data.layers_uv_select_src='ALL';data.layers_uv_select_dst='NAME';bpy.ops.object.datalayout_transfer(modifier=data.name);bpy.ops.object.modifier_apply(modifier=data.name)
 for f in ob.data.polygons:f.material_index=1
 donor.hide_set(True);return .00022

def top_xy(theta):
 # Same receiver mounting footprint, smoothly rounded corners. The lower end
 # is the actual per-grip boundary, never the common mounting footprint.
 direction=np.array([math.cos(theta),math.sin(theta)]);lo,hi=0.,.06;half=np.array([.0155,.0275]);radius=.0015
 for _ in range(28):
  r=(lo+hi)*.5;q=np.abs(direction*r)-(half-radius);sd=np.linalg.norm(np.maximum(q,0))+min(max(q),0)-radius
  if sd>0:hi=r
  else:lo=r
 return direction*((lo+hi)*.5)+np.array([.0008,.015])

def neck(ob,key,zcut,surface_index):
 me=ob.data;me.update();oldnorm=[n.vector.copy() for n in me.corner_normals];bm=bmesh.new();bm.from_mesh(me);bm.faces.ensure_lookup_table()
 normal_layers=[bm.loops.layers.float.new('J44OriginalN'+a) for a in 'xyz'];fresh=bm.faces.layers.int.new('J44NewFace')
 for f in bm.faces:
  for l,li in zip(f.loops,me.polygons[f.index].loop_indices):
   for k,layer in enumerate(normal_layers):l[layer]=oldnorm[li][k]
 # Weld only identical position splits introduced by FBX. Corner UV and
 # original normals stay in per-loop data before slicing.
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00000012)
 component=bm.verts.layers.int.new('J44SourceComponent');unassigned=set(bm.verts);components=[]
 while unassigned:
  seed=next(iter(unassigned));stack=[seed];group=set()
  while stack:
   v=stack.pop()
   if v not in unassigned:continue
   unassigned.remove(v);group.add(v);stack.extend(e.other_vert(v) for e in v.link_edges)
  idx=len(components)
  for v in group:v[component]=idx
  components.append(group)
 dominant=max(range(len(components)),key=lambda i:len(components[i]));(O/(key+'_components.json')).write_text(json.dumps(sorted([{'vertices':len(g),'zmin':min(v.co.z for v in g),'zmax':max(v.co.z for v in g)} for g in components],key=lambda r:-r['vertices'])[:20]))
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00000005,plane_co=(0,0,zcut),plane_no=(0,0,1),clear_outer=True,clear_inner=False)
 cutverts=[v for v in bm.verts if abs(v.co.z-zcut)<.000001]
 bmesh.ops.remove_doubles(bm,verts=cutverts,dist=.000005)
 edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-zcut)<.000001 for v in e.verts)]
 # Source surface tiles can have tiny pre-existing slits crossed by the cut.
 # Close only narrow slit chains crossing this neck, retaining their actual
 # edge vertices rather than merging distant points or altering the grip.
 plane_edges=set(edges);cut_ends={v for e in edges for v in e.verts if sum(v in q.verts for q in edges)==1};handled=set();patches=[];available={e for e in bm.edges if e.is_boundary and e not in plane_edges}
 for start in list(cut_ends):
  if start in handled:continue
  queue=[(0.,0,start)];distance={start:0.};prev={};seq=0;end=None
  while queue:
   dist,_,v=heapq.heappop(queue)
   if dist>distance[v]:continue
   if v!=start and v in cut_ends and v not in handled:end=v;break
   for e in v.link_edges:
    if e not in available:continue
    w=e.other_vert(v)
    if w.co.z<zcut-.012:continue
    dd=dist+(w.co-v.co).length
    if dd<distance.get(w,1e9):distance[w]=dd;prev[w]=(v,e);seq+=1;heapq.heappush(queue,(dd,seq,w))
  if end is None:raise RuntimeError('Source slit has no local endpoint '+key)
  if (end.co-start.co).length>.0012:raise RuntimeError('Source opening is not a narrow neck slit '+key)
  chain=[end];v=end
  while v!=start:v,e=prev[v];available.discard(e);chain.append(v)
  f=bm.faces.new(chain);f.material_index=surface_index;f.smooth=True;patches.append(f);handled.update([chain[0],chain[-1]])
  # Interpolate original corner attributes from the neighboring grip faces.
  for l in f.loops:
   donor=next((q for q in l.vert.link_loops if q.face!=f),None)
   if donor:
    for layer in normal_layers:l[layer]=donor[layer]
    for layer in bm.loops.layers.uv.values():l[layer].uv=donor[layer].uv
    for layer in list(bm.loops.layers.color.values())+list(bm.loops.layers.float_color.values()):l[layer]=donor[layer]
 if patches:bmesh.ops.triangulate(bm,faces=patches)
 edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-zcut)<.000001 for v in e.verts)]
 adj={}
 for e in edges:
  for v in e.verts:adj.setdefault(v,[]).append(e.other_vert(v))
 if not adj or any(len(ns)!=2 for ns in adj.values()):
  bad=[v for v,ns in adj.items() if len(ns)!=2];(O/(key+'_boundary.json')).write_text(json.dumps([{'p':list(v.co),'degree':len(adj[v]),'nearest_mm':min((v.co-w.co).length for w in bad if w!=v)*1000} for v in bad]));raise RuntimeError('Cannot form neck boundary '+key+' '+str(len(bad)))
 unseen=set(adj);loops=[]
 while unseen:
  start=next(iter(unseen));loop=[];last=None;v=start
  while True:
   loop.append(v);unseen.discard(v);n=next(n for n in adj[v] if n!=last);last,v=v,n
   if v==start:break
  area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))*.5
  if area<0:loop.reverse()
  loops.append((abs(area),loop))
 loops.sort(key=lambda x:x[0],reverse=True);base=loops[0][1];n=len(base)
 # Rare internal cut rings are closed locally; none remain as a duplicate
 # upper cap hidden beneath the newly authored neck.
 for area,loop in loops[1:]:
  face=bm.faces.new(loop);face.material_index=surface_index;face[fresh]=1
 center=sum((v.co for v in base),Vector())/n;positions=np.array([v.co[:] for v in base]);targets=np.array([top_xy(math.atan2(v.co.y-center.y,v.co.x-center.x)) for v in base]);height=.006-zcut
 base_norm=[];slopes=[];color_values=[]
 colors=list(bm.loops.layers.color.values())+list(bm.loops.layers.float_color.values())
 for v in base:
  normals=[Vector([l[a] for a in normal_layers]) for l in v.link_loops];normal=sum(normals,Vector()).normalized();base_norm.append(normal)
  den=max(normal.x**2+normal.y**2,.1);slope=np.array([-normal.z*normal.x/den,-normal.z*normal.y/den]);length=np.linalg.norm(slope)
  if length>.55:slope*=.55/length
  slopes.append(slope);color_values.append({layer:v.link_loops[0][layer][:] for layer in colors})
 slopes=np.array(slopes);uv0=bm.loops.layers.uv.get(me.uv_layers[0].name);mask_index=len(me.uv_layers)
 if mask_index>=8:raise RuntimeError('No free UV authoring channel '+key)
 mask=bm.loops.layers.uv.new('J44NeckMask')
 for f in bm.faces:
  for l in f.loops:
   l[mask].uv=(0,0)
   if f[fresh]:l[uv0].uv=(l.vert.co.x/.06,l.vert.co.y/.06)
 perimeter=np.r_[0,np.cumsum([float((base[(i+1)%n].co-base[i].co).length) for i in range(n)])];previous=base;newfaces=[];vertex_meta={v:(i,0.) for i,v in enumerate(base)}
 for t in [.035,.08,.16,.28,.43,.60,.76,.89,.97,1.]:
  smooth=t*t*(3-2*t);xy=positions[:,:2]*(1-smooth)+targets*smooth+slopes*height*t*(1-t)**2
  ring=[bm.verts.new((float(p[0]),float(p[1]),zcut+height*t)) for p in xy]
  for i,v in enumerate(ring):vertex_meta[v]=(i,t)
  for i in range(n):
   j=(i+1)%n;f=bm.faces.new((previous[i],previous[j],ring[j],ring[i]));f.material_index=surface_index;f.smooth=True;f[fresh]=1;newfaces.append(f)
   for l in f.loops:
    k,s=vertex_meta[l.vert];uu=perimeter[n if i==n-1 and k==0 else k]/.06;l[uv0].uv=(uu,s*height/.06);l[mask].uv=(s,0.)
    for layer,value in color_values[k].items():l[layer]=value
  previous=ring
 # The mounting top is a finite closed face inside the existing receiver.
 cap=bm.faces.new(previous);cap.material_index=surface_index;cap.smooth=False;cap[fresh]=1
 for l in cap.loops:l[uv0].uv=(l.vert.co.x/.06,l.vert.co.y/.06);l[mask].uv=(1,0)
 bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if f[fresh] and len(f.verts)>4]);bm.normal_update()
 for f in bm.faces:
  if not f[fresh]:continue
  for l in f.loops:
   if not f.smooth:nn=f.normal
   else:
    k,t=vertex_meta.get(l.vert,(0,1));blend=min(1.,t/.16);nn=(base_norm[k]*(1-blend)+l.vert.normal*blend).normalized()
   for k,layer in enumerate(normal_layers):l[layer]=nn[k]
 # Preserve all surviving source corner attributes, including their normals.
 normals=[Vector([l[a] for a in normal_layers]).normalized() for f in bm.faces for l in f.loops]
 bm.to_mesh(me);bm.free();me.update();me.normals_split_custom_set(normals);me.uv_layers.active_index=0
 for i,uv in enumerate(me.uv_layers):uv.active_render=i==0
 report[key]={'cut_z_m':zcut,'boundary_vertices':n,'boundary_loops':len(loops),'new_neck_top_m':.006,'mask_uv_channel':mask_index,'shared_boundary':True,'surface_slot':surface_index,'source_lower_uv_and_normals_preserved':True}
 ob.name='RearGrip_'+key+'_J44'

factory=bpy.data.objects['PistolGrip_G43'];localize(factory,root.inverted()@factory.matrix_world);neck(factory,'factory',-.018,0)
factory.data.materials[0]=bpy.data.materials.new('M_LMG201_FactoryRearGrip_J44');bind(factory)
seat=bpy.data.objects.get('FactoryGripSeat_G43')
if seat:bpy.data.objects.remove(seat,do_unlink=True)
select([factory,rig]);body=O/'Exports/SK_LMG201_J44_Grip.fbx';bpy.ops.export_scene.fbx(filepath=str(body),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
exports={}
for key in ['stable','balanced','phantom']:
 ob=bpy.data.objects['RearGrip_'+key+'_G43'];added=set();localize(ob,ob.matrix_world.copy())
 me=ob.data;bm=bmesh.new();bm.from_mesh(me)
 # Removing old seat faces must not discard the retained grip's corner data.
 layers=[bm.loops.layers.float.new('KeepN'+a) for a in 'xyz'];bm.faces.ensure_lookup_table()
 for f in bm.faces:
  for l,li in zip(f.loops,me.polygons[f.index].loop_indices):
   for k,layer in enumerate(layers):l[layer]=me.corner_normals[li].vector[k]
 surface=max(set(f.material_index for f in bm.faces),key=lambda i:sum(f.material_index==i for f in bm.faces));bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=surface],context='FACES')
 for f in bm.faces:f.material_index=1
 normals=[Vector([l[a] for a in layers]) for f in bm.faces for l in f.loops];bm.to_mesh(me);bm.free();me.update();me.normals_split_custom_set(normals)
 resolution=reconnect_source(ob,key);me=ob.data;neck(ob,key,-.018 if key!='phantom' else -.020,1);report[key]['source_reconnect_resolution_m']=resolution;report[key]['source_lower_uv_and_normals_preserved']=False;report[key]['source_uv_and_normals_transferred']=True;me.materials[1]=bpy.data.materials.new('M_LMG201_J44_'+key+'_Polymer')
 path=O/'Exports'/('SM_LMG201_J44_'+key+'.fbx');select([ob]);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE');exports[key]=str(path);ob.hide_render=True;ob.hide_set(True)
 for q in added:
  if q!=ob and q.name in bpy.data.objects:bpy.data.objects.remove(q,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_GripJunction44.blend'));(O/'model.json').write_text(json.dumps({'body_fbx':str(body),'grip_fbx':exports,'grips':report},indent=2));print('J44_MODEL_SAVED',json.dumps(report),flush=True)
