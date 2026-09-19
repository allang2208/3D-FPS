import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
out=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath='E:/3d/3-dfps/tools/chest-sapphire-20260908/warehouse_chest_v6.blend')
obj=bpy.data.objects['BodyAssembly'];old=obj.data
adj=[[] for v in old.vertices]
for e in old.edges:
 a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();components=[]
for start in range(len(adj)):
 if start in seen:continue
 q=[start];seen.add(start);ids=[]
 while q:
  v=q.pop();ids.append(v)
  for n in adj[v]:
   if n not in seen:seen.add(n);q.append(n)
 components.append(ids)
assert len(components)==136,len(components)
gold=next(i for i,m in enumerate(old.materials) if m.name=='Gold_PBR')
gem=next(i for i,m in enumerate(old.materials) if m.name=='Sapphire_PBR')
scroll_ids=list(range(82,94))+list(range(102,108))
petal_ids=list(range(20,64))
# 20..63 is precisely the 16 front rays and 14 rays on each side.
assert all(len(components[i])==8 for i in petal_ids)
old_setting_ids=[80,81,94,95,100,101,123,125,127,129,131,133,135]
removed={v for i in scroll_ids+petal_ids+old_setting_ids for v in components[i]}
oldfaces=[p for p in old.polygons if not any(v in removed for v in p.vertices)]
used=sorted({v for p in oldfaces for v in p.vertices});remap={v:i for i,v in enumerate(used)}
verts=[old.vertices[v].co.copy() for v in used]
faces=[[remap[v] for v in p.vertices] for p in oldfaces];slots=[p.material_index for p in oldfaces];smooth=[p.use_smooth for p in oldfaces]
# Seat each existing sapphire pavilion in the new bezel, preserving gem facets.
gem_moves=[]
for ids in components:
 ps=[p for p in old.polygons if p.vertices[0] in set(ids)]
 if not ps or not all(p.material_index==gem for p in ps):continue
 c=sum((old.vertices[i].co for i in ids),Vector())/len(ids)
 delta=Vector((0,0,0))
 if abs(c.x)>100:delta.x=-math.copysign(9.6,c.x)
 elif abs(c.x)<20:delta.y=12
 else:delta.y=9.1
 for i in ids:verts[remap[i]]+=delta
 gem_moves.append(list(delta))
assert len(gem_moves)==7

def append_mesh(mesh):
 offset=len(verts);verts.extend(v.co.copy() for v in mesh.vertices)
 for p in mesh.polygons:faces.append([offset+i for i in p.vertices]);slots.append(gold);smooth.append(p.use_smooth)

# The source scrollwork has disconnected polygon caps and low longitudinal sampling.
scrollverts={v for i in scroll_ids for v in components[i]}
sp=[p for p in old.polygons if p.vertices[0] in scrollverts]
sv=sorted(scrollverts);sm={v:i for i,v in enumerate(sv)}
co=[]
for i in sv:
 v=old.vertices[i].co.copy();v.y=-72.45+(v.y+83)*.60;co.append(v)
mesh=bpy.data.meshes.new('RefinedScrollwork');mesh.from_pydata(co,[],[[sm[v] for v in p.vertices] for p in sp]);mesh.update()
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.005);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
temp=bpy.data.objects.new('RefinedScrollwork',mesh);bpy.context.collection.objects.link(temp)
bpy.context.view_layer.objects.active=temp;temp.select_set(True)
sub=temp.modifiers.new('Silversmith smooth curves','SUBSURF');sub.levels=2;sub.render_levels=2
bpy.ops.object.modifier_apply(modifier=sub.name)
for p in temp.data.polygons:p.use_smooth=True
append_mesh(temp.data);bpy.data.objects.remove(temp,do_unlink=True)

contact=[]
def build_setting(center,u,v,n,rx,ry,back,outer):
 # Closed, rounded 96-sided bezel; 0.1 source units overlap with the backing panel.
 vv=[];ff=[];steps=96
 profile=[(outer-.04,-back),(outer,-back+.16),(outer,-.55),(outer-.015,-.28),(outer-.065,-.04),(1.01,.48),(.975,.48),(.975,.10),(.975,-back)]
 for scale,h in profile:
  for j in range(steps):
   a=math.tau*j/steps;vv.append(center+u*(rx*scale*math.cos(a))+v*(ry*scale*math.sin(a))+n*h)
 for row in range(len(profile)):
  nr=(row+1)%len(profile)
  for j in range(steps):k=(j+1)%steps;ff.append((row*steps+j,row*steps+k,nr*steps+k,nr*steps+j))
 emit(vv,ff,True)
 contact.append({'bezel_center':list(center),'back_world_local':list(center-n*back),'outer_radius':[rx*outer,ry*outer]})

def emit(vv,ff,shading):
 mesh=bpy.data.meshes.new('OrnamentPiece');mesh.from_pydata(vv,[],ff);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 for p in mesh.polygons:p.use_smooth=shading
 append_mesh(mesh);bpy.data.meshes.remove(mesh)

def rays(center,u,v,n,count,inner,outer,halfwidth):
 # Lenticular relief rays. Each root intersects the bezel and each back overlaps marble.
 for k in range(count):
  a=math.tau*k/count;d=u*math.cos(a)+v*math.sin(a);side=-u*math.sin(a)+v*math.cos(a)
  vv=[];ff=[];length=outer-inner;steps=14;cross=8
  for back in [False,True]:
   for j in range(steps+1):
    t=j/steps;width=halfwidth*(.09+.91*math.sin(math.pi*(.20+.80*t))**.8)
    if j==steps:width=.09
    for l in range(cross+1):
     s=-1+2*l/cross
     h=-.10 if back else .24+(2.30*(1-t)+.45)*max(0,1-s*s)**.6
     vv.append(center+d*(inner+length*t)+side*(width*s)+n*h)
  sheet=(steps+1)*(cross+1)
  for layer in [0,1]:
   for j in range(steps):
    for l in range(cross):
     p=layer*sheet+j*(cross+1)+l;face=(p,p+1,p+cross+2,p+cross+1);ff.append(face if layer==0 else tuple(reversed(face)))
  boundary=list(range(cross+1))+[j*(cross+1)+cross for j in range(1,steps+1)]+[steps*(cross+1)+l for l in range(cross-1,-1,-1)]+[j*(cross+1) for j in range(steps-1,0,-1)]
  for i,p in enumerate(boundary):q=boundary[(i+1)%len(boundary)];ff.append((p,q,q+sheet,p+sheet))
  emit(vv,ff,True)
 contact.append({'ray_back_plane':list(center-n*.10),'ray_root':inner,'ray_tip':outer,'count':count})

build_setting(Vector((0,-77,64.16)),Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0)),14.3,14.8,6.10,1.30)
rays(Vector((0,-71,64.16)),Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0)),16,17.7,26,3.1)
for x in [-78,-50,50,78]:build_setting(Vector((x,-76.5,39)),Vector((1,0,0)),Vector((0,0,1)),Vector((0,-1,0)),5,6.1,5.60,1.12)
for s in [-1,1]:
 build_setting(Vector((s*104.6,0,59)),Vector((0,1,0)),Vector((0,0,1)),Vector((s,0,0)),11.2,12,6.70,1.40)
 rays(Vector((s*98,0,59)),Vector((0,1,0)),Vector((0,0,1)),Vector((s,0,0)),14,14.8,24,2.9)

new=bpy.data.meshes.new('BodyFittedOrnamentsV7');new.from_pydata(verts,[],faces);new.update()
for mat in old.materials:new.materials.append(mat)
for p,slot,sm in zip(new.polygons,slots,smooth):p.material_index=slot;p.use_smooth=sm
uv=new.uv_layers.new(name='UVMap')
for p in new.polygons:
 for li in p.loop_indices:
  c=new.vertices[new.loops[li].vertex_index].co
  uv.data[li].uv=((c.y if abs(c.x)>96 else c.x)*.002,c.z*.002)
for p,oldp in zip(new.polygons,oldfaces):
 for a,b in zip(p.loop_indices,oldp.loop_indices):uv.data[a].uv=old.uv_layers.active.data[b].uv
normals=[n.vector.copy() for n in new.corner_normals]
for p,oldp in zip(new.polygons,oldfaces):
 for a,b in zip(p.loop_indices,oldp.loop_indices):normals[a]=old.corner_normals[b].vector.copy()
new.normals_split_custom_set(normals);obj.data=new
root=bpy.data.objects['WarehouseChest'];hinge=bpy.data.objects['LidHinge'];latch=bpy.data.objects['WarehouseChest_LidLatch']
bpy.context.scene.frame_set(0)
for o in [hinge,latch]:
 for track in o.animation_data.nla_tracks:track.mute=True
hinge.rotation_euler.x=0
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'warehouse_chest_v7.blend'))
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children_recursive:o.select_set(True)
for o in [hinge,latch]:
 for track in o.animation_data.nla_tracks:track.mute=False
bpy.ops.export_scene.gltf(filepath=str(out/'warehouse_chest_v7.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_force_sampling=True,export_frame_range=False)
report={'gem_moves_local':gem_moves,'scroll_components_smoothed':len(scroll_ids),'rays_rebuilt':44,'bezels_rebuilt':7,'source_unit_m':.007,'contact':contact,'old_vertices':len(old.vertices),'new_vertices':len(new.vertices),'old_faces':len(old.polygons),'new_faces':len(new.polygons)}
(out/'geometry_report.json').write_text(json.dumps(report,indent=2))
print('CHEST_ORNAMENTS_BUILD_PASS',report)
