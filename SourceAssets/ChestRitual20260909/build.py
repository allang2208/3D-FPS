import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
out=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='E:/3d/3-dfps/tools/chest-sapphire-20260908/warehouse_chest_v6.blend')
def components(m):
 adj=[[] for v in m.vertices]
 for e in m.edges:
  a,b=e.vertices;adj[a].append(b);adj[b].append(a)
 seen=set();result=[]
 for start in range(len(adj)):
  if start in seen:continue
  q=[start];seen.add(start);ids=[]
  while q:
   v=q.pop();ids.append(v)
   for n in adj[v]:
    if n not in seen:seen.add(n);q.append(n)
  result.append(ids)
 return result

def material(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 return m
accent=material('Ritual_Champagne',(.32,.265,.17),.94,.28)
plate=material('Ritual_Gunmetal',(.12,.145,.17),.95,.38)
groove=material('Ritual_Engraving',(.018,.024,.032),.70,.55)
for name in ['Gold_PBR','Brass_Frame','Brass_Strap','Brass_Hardware']:
 m=bpy.data.materials[name];p=m.node_tree.nodes.get('Principled BSDF')
 if p:p.inputs['Base Color'].default_value=(.12,.145,.17,1);p.inputs['Roughness'].default_value=.36
gemmat=bpy.data.materials['Sapphire_PBR'];p=gemmat.node_tree.nodes.get('Principled BSDF')
if p:p.inputs['Base Color'].default_value=(.004,.015,.055,1);p.inputs['Metallic'].default_value=.03;p.inputs['Roughness'].default_value=.14

obj=bpy.data.objects['BodyAssembly'];old=obj.data;comps=components(old)
assert len(comps)==136
remove_ids=[0,108]+list(range(20,64))+list(range(80,96))+list(range(100,108))+list(range(122,136))
removed={v for i in remove_ids for v in comps[i]}
oldfaces=[p for p in old.polygons if not any(v in removed for v in p.vertices)]
used=sorted({v for p in oldfaces for v in p.vertices});remap={v:i for i,v in enumerate(used)}
verts=[old.vertices[i].co.copy() for i in used];faces=[[remap[v] for v in p.vertices] for p in oldfaces]
mats=list(old.materials)+[accent,plate,groove];slots=[p.material_index for p in oldfaces];smooth=[p.use_smooth for p in oldfaces]
gi=next(i for i,m in enumerate(mats) if m.name=='Sapphire_PBR');ai=len(mats)-3;pi=len(mats)-2;ei=len(mats)-1
parts=[]
def emit(vv,ff,slot,sm=False,bevel=0):
 mesh=bpy.data.meshes.new('RitualDetail');mesh.from_pydata(vv,[],ff);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 if bevel:
  bmesh.ops.bevel(bm,geom=list(bm.edges),offset=bevel,segments=3,affect='EDGES')
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 bm.to_mesh(mesh);bm.free();off=len(verts)
 verts.extend(v.co.copy() for v in mesh.vertices)
 for p in mesh.polygons:faces.append([off+i for i in p.vertices]);slots.append(slot);smooth.append(sm)
 bpy.data.meshes.remove(mesh)

def bezel(c,u,v,n,rx,ry,back):
 vv=[];ff=[];N=96
 for scale,h in [(1.10,-back),(1.135,-back+.14),(1.135,-.12),(1.105,.18),(.98,.25),(.975,-back)]:
  for i in range(N):
   a=math.tau*i/N;vv.append(c+u*(rx*scale*math.cos(a))+v*(ry*scale*math.sin(a))+n*h)
 for r in range(6):
  for i in range(N):j=(i+1)%N;nr=(r+1)%6;ff.append((r*N+i,r*N+j,nr*N+j,nr*N+i))
 emit(vv,ff,ai,True)

def badge(c,u,v,n,radius):
 # A closed, thin dial with real recessed radial cuts; no detached petals.
 N=360;rr=[0,.61*radius,.72*radius,.82*radius,.925*radius,radius]
 cells={};vv=[];ff=[];face_slots=[]
 for r in range(len(rr)-1):
  for i in range(N):
   tick=i%15==0 and (r==3 or (r==2 and (i//15)%2==0))
   cells[r,i]=.30 if tick else .68
 for (r,i),h in cells.items():
  a=math.tau*i/N;b=math.tau*(i+1)/N
  xy=[(rr[r],a),(rr[r],b),(rr[r+1],b),(rr[r+1],a)]
  start=len(vv)
  vv.extend(c+u*(rad*math.cos(ang))+v*(rad*math.sin(ang))+n*h for rad,ang in xy)
  ff.append(tuple(start+j for j in range(4)));face_slots.append(ei if h<.5 else pi)
  for edge,neighbor in [(0,(r-1,i)),(1,(r,(i+1)%N)),(2,(r+1,i)),(3,(r,(i-1)%N))]:
   nh=cells.get(neighbor,-.1)
   if nh>=h:continue
   j=edge;k=(edge+1)%4;st=len(vv)
   vv.extend([vv[start+j],vv[start+k],vv[start+k]-n*(h-nh),vv[start+j]-n*(h-nh)])
   ff.append((st,st+1,st+2,st+3));face_slots.append(pi)
 # bottom fan closes the disk
 for i in range(N):
  a=math.tau*i/N;b=math.tau*(i+1)/N;st=len(vv)
  vv.extend([c-n*.1,c+u*(radius*math.cos(a))+v*(radius*math.sin(a))-n*.1,c+u*(radius*math.cos(b))+v*(radius*math.sin(b))-n*.1]);ff.append((st,st+1,st+2));face_slots.append(pi)
 off=len(verts);verts.extend(vv)
 for f,slot in zip(ff,face_slots):faces.append([off+i for i in f]);slots.append(slot);smooth.append(False)
 # Slim outer champagne rim, flush to the disk edge.
 vv=[];ff=[]
 for rad,h in [(radius-.24,.67),(radius-.24,.84),(radius-.07,.84),(radius-.07,.67)]:
  for i in range(N):
   a=math.tau*i/N;vv.append(c+u*(rad*math.cos(a))+v*(rad*math.sin(a))+n*h)
 for r in range(4):
  for i in range(N):j=(i+1)%N;nr=(r+1)%4;ff.append((r*N+i,r*N+j,nr*N+j,nr*N+i))
 emit(vv,ff,ai,True)
 parts.append({'badge_center':list(c),'radius_source':radius,'back_overlap_mm':.7,'engraved_ticks':24,'engraving_depth_mm':2.66})

def gem_from_component(cid,c_old,c_new,scale):
 ids=comps[cid];ss=set(ids);ps=[p for p in old.polygons if p.vertices[0] in ss];mp={v:i for i,v in enumerate(ids)}
 vv=[c_new+(old.vertices[i].co-c_old)*scale for i in ids]
 emit(vv,[[mp[i] for i in p.vertices] for p in ps],gi,False)

u=Vector((1,0,0));v=Vector((0,0,1));n=Vector((0,-1,0))
gem_from_component(122,Vector((0,-89,64.16)),Vector((0,-73.6,64.16)),.72)
bezel(Vector((0,-73.6,64.16)),u,v,n,14.3*.72,14.8*.72,1.95)
badge(Vector((0,-71,64.16)),u,v,n,20.8)
for s,cid in [(-1,132),(1,134)]:
 u=Vector((0,1,0));n=Vector((s,0,0))
 gem_from_component(cid,Vector((s*114.2,0,59)),Vector((s*100.3,0,59)),.72)
 bezel(Vector((s*100.3,0,59)),u,v,n,11.2*.72,12*.72,1.65)
 badge(Vector((s*98,0,59)),u,v,n,17)

def line(a,b,width=.36,slot=ai):
 d=(b-a).normalized();perp=Vector((-d.z,0,d.x))*width/2;n=Vector((0,-1,0));vv=[]
 for h in [-.10,.20]:vv += [a-perp+n*h,b-perp+n*h,b+perp+n*h,a+perp+n*h]
 emit(vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],slot,False,.04)

# Restrained paired stepped corner inlays on the otherwise open marble fields.
for side in [-1,1]:
 for lower in [False,True]:
  z=43 if lower else 80;direction=1 if lower else -1
  for inset in [0,2]:
   points=[(side*(82-inset),z+direction*14),(side*(82-inset),z+direction*inset),(side*(70-inset),z+direction*inset),(side*(70-inset),z+direction*(4+inset)),(side*43,z+direction*(4+inset))]
   for a,b in zip(points,points[1:]):line(Vector((a[0],-71,a[1])),Vector((b[0],-71,b[1])),.30 if inset else .44,ai if inset else pi)

new=bpy.data.meshes.new('BodyColdSteelRitualV8');new.from_pydata(verts,[],faces);new.update()
for m in mats:new.materials.append(m)
for p,slot,sm in zip(new.polygons,slots,smooth):p.material_index=slot;p.use_smooth=sm
uv=new.uv_layers.new(name='UVMap')
for p in new.polygons:
 for li in p.loop_indices:
  c=new.vertices[new.loops[li].vertex_index].co;uv.data[li].uv=((c.y if abs(c.x)>96 else c.x)*.002,c.z*.002)
for p,op in zip(new.polygons,oldfaces):
 for a,b in zip(p.loop_indices,op.loop_indices):uv.data[a].uv=old.uv_layers.active.data[b].uv
normals=[n.vector.copy() for n in new.corner_normals]
for p,op in zip(new.polygons,oldfaces):
 for a,b in zip(p.loop_indices,op.loop_indices):normals[a]=old.corner_normals[b].vector.copy()
new.normals_split_custom_set(normals);obj.data=new

# Remove the previous raised gold laurel leaves from the lid straps.
lid=bpy.data.objects['LidAssembly'];lm=lid.data;lc=components(lm)
removed_lid=set();leaf_count=0
for ids in lc:
 if len(ids)==27:
  ps=[p for p in lm.polygons if p.vertices[0] in set(ids)]
  if ps and all(lm.materials[p.material_index].name=='Gold_PBR' for p in ps):removed_lid.update(ids);leaf_count+=1
assert leaf_count==48,leaf_count
lp=[p for p in lm.polygons if p.vertices[0] not in removed_lid];lu=sorted({v for p in lp for v in p.vertices});mp={v:i for i,v in enumerate(lu)}
ln=bpy.data.meshes.new('LidColdSteelRitualV8');ln.from_pydata([lm.vertices[i].co for i in lu],[],[[mp[i] for i in p.vertices] for p in lp]);ln.update()
for m in lm.materials:ln.materials.append(m)
luv=ln.uv_layers.new(name='UVMap');nn=[n.vector.copy() for n in ln.corner_normals]
for p,op in zip(ln.polygons,lp):
 p.material_index=op.material_index;p.use_smooth=op.use_smooth
 for a,b in zip(p.loop_indices,op.loop_indices):luv.data[a].uv=lm.uv_layers.active.data[b].uv;nn[a]=lm.corner_normals[b].vector.copy()
ln.normals_split_custom_set(nn);lid.data=ln
root=bpy.data.objects['WarehouseChest'];hinge=bpy.data.objects['LidHinge'];latch=bpy.data.objects['WarehouseChest_LidLatch'];bpy.context.scene.frame_set(0)
for o in [hinge,latch]:
 for t in o.animation_data.nla_tracks:t.mute=True
hinge.rotation_euler.x=0
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'warehouse_chest_ritual_v8.blend'))
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children_recursive:o.select_set(True)
for o in [hinge,latch]:
 for t in o.animation_data.nla_tracks:t.mute=False
bpy.ops.export_scene.gltf(filepath=str(out/'warehouse_chest_ritual_v8.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_frame_range=False)
(out/'geometry_report.json').write_text(json.dumps({'badges':parts,'gems':3,'removed_small_gems':4,'removed_lid_leaves':leaf_count,'body_vertices':len(new.vertices),'body_faces':len(new.polygons)},indent=2))
print('RITUAL_GEOMETRY_PASS')
