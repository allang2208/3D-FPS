import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
R=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(R.parent/'foreman-howl-v10-20260908/foreman-animated.blend'))
a=bpy.data.objects['ForemanRig'];s=bpy.context.scene;s.render.fps=80;o=bpy.data.objects['LeftArmFinished']
def sig(ac,exclude=False):
 return {(f.data_path,f.array_index):[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation) for k in f.keyframe_points] for l in ac.layers for st in l.strips for b in st.channelbags for f in b.fcurves if not(exclude and any('"'+n+'"' in f.data_path for n in ['upper_arm.L','forearm.L','hand.L']))}
saved={ac.name:sig(ac,ac.name in ['Walk','Death','Howl']) for ac in bpy.data.actions}
# Relax only the rebuilt cloth surface, holding its open attachment boundary.
bm=bmesh.new();bm.from_mesh(o.data)
cloth={v for f in bm.faces if f.material_index==3 for v in f.verts};fixed={v for v in bm.verts if v.is_boundary or any(f.material_index!=3 for f in v.link_faces)}
for step in range(4):
 updates={v:v.co.lerp(sum((e.other_vert(v).co for e in v.link_edges),Vector())/len(v.link_edges),.22) for v in cloth-fixed if v.link_edges}
 for v,p in updates.items():v.co=p
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
for f in o.data.polygons:f.use_smooth=True
bpy.context.view_layer.objects.active=o;o.hide_set(False)
if o.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
mat=o.data.materials[3].copy();mat.name='LeftSleeveRefined';o.data.materials[3]=mat
uv=o.data.uv_layers.active
for f in o.data.polygons:
 if f.material_index==3:
  for li in f.loop_indices:uv.data[li].uv.x=.54+.44*(uv.data[li].uv.x%1.0)
for node in mat.node_tree.nodes:
 if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.18
# Add deformation samples without shrinking the original hand silhouette or changing UVs.
bpy.context.view_layer.objects.active=o;o.hide_set(False)
sub=o.modifiers.new('DeformationSamples','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=1
bpy.ops.object.modifier_move_up(modifier=sub.name);bpy.ops.object.modifier_apply(modifier=sub.name)
E=a.data.bones['forearm.L'].head_local;W=a.data.bones['hand.L'].head_local;axis=(W-E).normalized()
def smooth(lo,hi,x):
 u=max(0,min(1,(x-lo)/(hi-lo)));return u*u*(3-2*u)
cloth={v for f in o.data.polygons if f.material_index==3 for v in f.vertices}
weights=[]
for v in o.data.vertices:
 if v.index in cloth:weights.append([1.,0.,0.]);continue
 d=(v.co-E).dot(axis);h=smooth(-.045,.065,(v.co-W).dot(axis));f=smooth(-.055,.075,d)*(1-h);weights.append([1-f-h,f,h])
# Adjacency smoothing, with the sleeve/cuff interface pinned to a shared driver.
adj=[set() for v in o.data.vertices]
for e in o.data.edges:
 i,j=e.vertices;adj[i].add(j);adj[j].add(i)
for step in range(3):
 old=[v[:] for v in weights]
 for i,ns in enumerate(adj):
  if i in cloth or not ns:continue
  weights[i]=[old[i][k]*.65+.35*sum(old[j][k] for j in ns)/len(ns) for k in range(3)]
for v,w in zip(o.data.vertices,weights):
 for g in list(v.groups):o.vertex_groups[g.group].remove([v.index])
 for n,x in zip(['upper_arm.L','forearm.L','hand.L'],w):
  if x>1e-7:o.vertex_groups[n].add([v.index],x,'REPLACE')
# Correct disconnected IK heads in Howl; add restrained wrist overlap in Walk/Death.
for name,duration in [('Walk',1.5),('Death',1.4),('Howl',3)]:
 ac=bpy.data.actions[name];a.animation_data.action=ac;a.animation_data.action_slot=ac.slots[0];frames=[]
 for i in range(round(duration*80)+1):
  s.frame_set(i);frames.append({n:a.pose.bones[n].matrix_basis.copy() for n in ['upper_arm.L','forearm.L','hand.L']})
 previous={}
 for i,base in enumerate(frames):
  s.frame_set(i);t=i/80
  for n,m in base.items():a.pose.bones[n].matrix_basis=m
  bpy.context.view_layer.update()
  for n in ['upper_arm.L','forearm.L','hand.L']:
   p=a.pose.bones[n];m=p.matrix.copy();m.translation=p.parent.tail;p.matrix=m;bpy.context.view_layer.update()
  p=a.pose.bones['hand.L'];p.rotation_mode='QUATERNION'
  angle=.06*math.sin(t/1.5*math.tau-.5) if name=='Walk' else (.065*math.sin(math.pi*smooth(.3,1.28,t))**2 if name=='Death' else -.04*math.sin(math.pi*t/3)**2)
  p.rotation_quaternion=p.rotation_quaternion@Quaternion(Vector((1,0,0)),angle)
  for n in base:
   p=a.pose.bones[n];p.rotation_mode='QUATERNION'
   if n in previous and p.rotation_quaternion.dot(previous[n])<0:p.rotation_quaternion.negate()
   previous[n]=p.rotation_quaternion.copy()
   for ch in ['location','rotation_quaternion','scale']:p.keyframe_insert(ch,frame=i)
 for l in ac.layers:
  for st in l.strips:
   for bag in st.channelbags:
    for f in bag.fcurves:
     if any('"'+n+'"' in f.data_path for n in ['upper_arm.L','forearm.L','hand.L']):
      for k in f.keyframe_points:k.interpolation='LINEAR'
assert all(sig(bpy.data.actions[n],n in ['Walk','Death','Howl'])==v for n,v in saved.items())
(R/'changes.json').write_text(json.dumps({'left_vertices':len(o.data.vertices),'weights':'bone-axis gradients and adjacency smoothing; cuff interface pinned','geometry':'cloth relaxation, smooth normals, simple subdivision preserves hand outline','unchanged_channels':{n:len(v) for n,v in saved.items()},'rest_bones_changed':False},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-animated.blend'));bpy.ops.object.select_all(action='DESELECT');a.select_set(True)
for ob in s.objects:
 if ob.type=='MESH' and any(m.type=='ARMATURE' and m.object==a for m in ob.modifiers):ob.select_set(True)
bpy.context.view_layer.objects.active=a;bpy.ops.export_scene.gltf(filepath=str(R/'foreman-animated.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_force_sampling=True,export_frame_range=False)
print('LEFT_REFINE_COMPLETE')
