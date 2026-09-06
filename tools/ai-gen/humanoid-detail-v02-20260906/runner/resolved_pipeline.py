VARIANT='runner'
"""Denys native zombie motion + CC0 UAL death/hit retarget, textured for our game."""
import bpy,bmesh,json,math,statistics
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('E:\\3d\\3-dfps\\tools\\ai-gen\\humanoid-detail-v02-20260906\\runner'); SOURCE=Path('E:\\3d\\3-dfps\\tools\\ai-gen\\modern-zombie-v01-20260906')
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'denys-A-motions.gltf'))
a=next(o for o in s.objects if o.type=='ARMATURE')
body=next(o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers))
for tr in a.animation_data.nla_tracks:tr.mute=True
a.animation_data.action=None
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
native={act.name:act for act in bpy.data.actions}
for act in native.values():act.use_fake_user=True
def set_action(rig,act):
 rig.animation_data.action=act
 if act.slots:rig.animation_data.action_slot=act.slots[0]
def curves(act):
 return [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
def alias(original,name,speed=1):
 act=native[original].copy();act.name=name;act.use_fake_user=True
 for fc in curves(act):
  for k in fc.keyframe_points:
   k.co.x/=speed;k.handle_left.x/=speed;k.handle_right.x/=speed
 if name in ['Idle','Walk']:
  end=act.frame_range[1]
  for fc in curves(act):
   if len(fc.keyframe_points)<2:continue
   correction=fc.keyframe_points[0].co.y-fc.keyframe_points[-1].co.y
   for k in fc.keyframe_points:
    t=max(0.,min(1.,(k.co.x-(end-6))/6));offset=correction*t*t*(3-2*t)
    k.co.y+=offset;k.handle_left.y+=offset;k.handle_right.y+=offset
 return act
alias('idle_220f','Idle');alias('running_58f','Walk')
alias('attack_left_70f','Attack',70/47);alias('attack_right_70f','AttackRight',70/47)

# Bring the public UAL donor into the same Blender world axes before retargeting.
existing=set(s.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'ual-mannequin.glb'))
donor_objects=set(s.objects)-existing
donor=next(o for o in donor_objects if o.type=='ARMATURE')
for tr in donor.animation_data.nla_tracks:tr.mute=True
donor.animation_data.action=None
for pb in donor.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
target_rest={b.name:a.matrix_world@b.matrix_local for b in a.data.bones}
source_rest={b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones}
mapping={'bip':'Hips','bip Pelvis':'Hips','bip Spine':'Spine','bip Spine1':'UpperChest','bip Neck':'Neck','bip Head':'Head'}
for side,word in [('L','Left'),('R','Right')]:
 for dst,src in [('Clavicle','Shoulder'),('UpperArm','UpperArm'),('Forearm','LowerArm'),('Hand','Hand'),('Thigh','UpperLeg'),('Calf','LowerLeg'),('Foot','Foot'),('Toe0','Toes'),('Finger0','ThumbProximal'),('Finger01','ThumbDistal'),('Finger1','IndexProximal'),('Finger11','IndexIntermediate')]:mapping['bip '+side+' '+dst]=word+src
scale_ratio=target_rest['bip'].translation.z/source_rest['Hips'].translation.z
retarget_report={}
for source_name,new_name in [('Death01','Death'),('Hit_Chest','HitReact')]:
 source_action=bpy.data.actions[source_name]
 set_action(donor,source_action)
 result=bpy.data.actions.new(new_name);result.use_fake_user=True
 a.animation_data.action=result
 samples=round(source_action.frame_range[1]*2)
 minimum=1e9;baseline_low=None
 for step in range(samples+1):
  frame=step/2
  s.frame_set(int(frame),subframe=frame%1)
  for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
  bpy.context.view_layer.update()
  for pb in a.pose.bones:
   if pb.name not in mapping:continue
   source_bone=mapping[pb.name]
   posed=donor.matrix_world@donor.pose.bones[source_bone].matrix
   rot=posed.to_quaternion()@source_rest[source_bone].to_quaternion().inverted()@target_rest[pb.name].to_quaternion()
   if pb.parent:
    offset=pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local
    position=(a.matrix_world@pb.parent.matrix@offset).translation
   else:
    source_hip=(donor.matrix_world@donor.pose.bones['Hips'].matrix).translation
    position=source_hip*scale_ratio
   desired=rot.to_matrix().to_4x4();desired.translation=position
   pb.matrix=a.matrix_world.inverted()@desired
   bpy.context.view_layer.update()
  # Keep the sole / body contact on the plane after changing limb proportions.
  evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
  low=min((evaluated.matrix_world@v.co).z for v in mesh.vertices);evaluated.to_mesh_clear()
  if baseline_low is None:baseline_low=low
  correction=max(-baseline_low,-low)
  root=a.pose.bones['bip'];mat=a.matrix_world@root.matrix;mat.translation.z+=correction;root.matrix=a.matrix_world.inverted()@mat
  minimum=min(minimum,low*.01)
  for pb in a.pose.bones:
   pb.rotation_mode='QUATERNION'
   pb.keyframe_insert('location',frame=frame,group=pb.name)
   pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
   pb.keyframe_insert('scale',frame=frame,group=pb.name)
 for fc in curves(result):
  for key in fc.keyframe_points:key.interpolation='LINEAR'
 retarget_report[new_name]={'source':source_name,'duration':source_action.frame_range[1]/30,'samples':samples+1,'initial_low_before_contact_correction_m':minimum}
for obj in donor_objects:bpy.data.objects.remove(obj,do_unlink=True)
for name in ['Death01','Death02','Hit_Chest']:
 if name in bpy.data.actions:bpy.data.actions.remove(bpy.data.actions[name])

# Record actual foot support speed from the existing in-place limp cycle.
set_action(a,bpy.data.actions['Walk']);foot_samples={'L':[],'R':[]}
for frame in range(round(bpy.data.actions['Walk'].frame_range[1])+1):
 s.frame_set(frame);bpy.context.view_layer.update()
 for side in foot_samples:foot_samples[side].append((a.matrix_world@a.pose.bones['bip '+side+' Foot'].matrix).translation.copy()*.01)
speeds=[]
for points in foot_samples.values():
 floor=min(p.z for p in points)
 for prev,nxt in zip(points,points[1:]):
  if prev.z<floor+.045 and nxt.z<floor+.045:
   speed=Vector((nxt.x-prev.x,nxt.y-prev.y)).length*30
   if .04<speed<6.0:speeds.append(speed)
walk_reference=statistics.median(speeds) if speeds else .5
a.animation_data.action=None
for pb in a.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()

# Semantic material regions derived from the source palette and T-pose anatomy.
palette=bpy.data.images.get('zcolors.png') or next(im for im in bpy.data.images if im.size[0]>1)
pixels=list(palette.pixels);w,h=palette.size
regions=['Skin','Shirt','Trousers','Hair','Leather','DriedBlood','Eyes','HardHat','Reflective','Metal','Lamp']
regions += ['Tie']
face_regions=[]
old_uv=body.data.uv_layers.active
for poly in body.data.polygons:
 co=sum((body.matrix_world@body.data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
 uv=old_uv.data[poly.loop_indices[0]].uv
 index=4*(min(h-1,max(0,int(uv.y*h)))*w+min(w-1,max(0,int(uv.x*w))))
 red,green,blue=pixels[index:index+3]
 skin_area=co.z>143 or abs(co.x)>59
 if co.z<14:region='Leather'
 elif co.z<84:region='Trousers'
 elif skin_area:
  if co.z>154 and red>green*1.35 and red<.4:region='Hair'
  elif red<.025 and green<.025:region='Eyes'
  elif red>green*1.7 and red>.04:region='DriedBlood'
  else:region='Skin'
 elif red>green*1.7 and red>.04:region='DriedBlood'
 elif abs(co.x)<6 and co.y<0 and red<.16:region='Leather'
 else:region='Shirt'
 if region=='DriedBlood' and abs(co.x)<5 and 96<co.z<134:region='Shirt'
 if VARIANT=='runner' and region=='Shirt' and abs(co.x)>25 and co.z>127:region='Skin'
 face_regions.append(regions.index(region))
body.data.materials.clear()
for region in regions:body.data.materials.append(bpy.data.materials.new(VARIANT+'_'+region))
for poly,region in zip(body.data.polygons,face_regions):poly.material_index=region;poly.use_smooth=True
# UV seams and palette shading splits can be welded only with identical skin.
bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bm.normal_update();bm.to_mesh(body.data);bm.free()
for v in body.data.vertices:
 weights=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-8],key=lambda x:-x[1])[:4];total=sum(w for _,w in weights);assert total>0
 for g in body.vertex_groups:g.remove([v.index])
 for i,value in weights:body.vertex_groups[i].add([v.index],value/total,'REPLACE')
# Rest-pose detail in Blender world centimetres, before variant attachments.
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
original_points=[body.matrix_world@v.co for v in body.data.vertices]
original_surface=BVHTree.FromPolygons(original_points,[list(p.vertices) for p in body.data.polygons])
tri_before=sum(len(p.vertices)-2 for p in body.data.polygons)
# Recover compatible quads first, then add curved support across anatomical joints.
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.join_triangles(bm,faces=list(bm.faces),angle_face_threshold=.52,angle_shape_threshold=.55,cmp_uvs=False,cmp_vcols=False,cmp_seam=False,cmp_sharp=False,cmp_materials=True)
bm.to_mesh(body.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
sub=body.modifiers.new('Anatomical surface support','SUBSURF');sub.levels=1;sub.render_levels=1
bpy.ops.object.modifier_apply(modifier=sub.name)
# User correction: retain the simple Low Poly face; no extra face/hand subdivision.
inverse=body.matrix_world.inverted()
def gaussian(x,y,cx,cy,sx,sy):return math.exp(-((x-cx)/sx)**2-((y-cy)/sy)**2)
for v in body.data.vertices:
 p=body.matrix_world@v.co
 closest,normal,idx,dist=original_surface.find_nearest(p)
 # Preserve thin fingers and the planted sole while softening low-poly shoulders.
 restore=.90 if p.z<10 or p.z>145 else (.75 if abs(p.x)>64 else .62)
 if closest is not None:p=p.lerp(closest,restore)
 # Small anatomical knuckle relief along the hand, retaining the source finger chains.
 if 68<abs(p.x)<81 and 133<p.z<141:
  p.z+=.16*math.exp(-((abs(p.x)-73)/2.0)**2)*(.65+.35*math.cos(p.y*1.4))
 # Actual folds at knee, elbow and waist. Amplitudes are centimetres, not metres.
 joint=math.exp(-((p.z-49)/6)**2) if abs(p.x)<22 else math.exp(-((abs(p.x)-42)/5)**2)
 if (18<p.z<85 and abs(p.x)<23) or (125<p.z<145 and 25<abs(p.x)<60):
  n=(body.matrix_world.to_3x3()@v.normal).normalized()
  fold=.24*joint*math.sin(p.z*1.5+abs(p.x)*.25)+.06*math.sin(p.z*.7+p.x*.45)
  p+=n*fold
 if 86<p.z<106 and abs(p.x)<19:
  n=(body.matrix_world.to_3x3()@v.normal).normalized()
  p+=n*(.23*math.sin(p.z*1.2+p.x*.22)*math.exp(-((p.z-94)/8)**2))
 v.co=inverse@p
# Remove polygon-shaped blood blocks; new surface masks define rounded irregular injuries.
for p in body.data.polygons:
 co=sum((body.matrix_world@body.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
 if regions[p.material_index]=='DriedBlood':
  if co.z>145:
   region='DriedBlood'
  elif abs(co.x)>59 or (VARIANT=='runner' and abs(co.x)>25 and co.z>127):region='Skin'
  else:region='Shirt'
  p.material_index=regions.index(region)
 p.use_smooth=True
# Interpolation can produce more than four influences; keep the strongest and normalize.
for v in body.data.vertices:
 weights=sorted([(g.group,g.weight) for g in v.groups if g.weight>1e-8],key=lambda q:-q[1])[:4]
 total=sum(w for _,w in weights);assert total>0
 for g in body.vertex_groups:g.remove([v.index])
 for i,w in weights:body.vertex_groups[i].add([v.index],w/total,'REPLACE')
surface=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons])
kd=KDTree(len(body.data.vertices))
for v in body.data.vertices:kd.insert(body.matrix_world@v.co,v.index)
kd.balance()
details=[]
def detail_bind(obj,name,region,bone=None):
 obj.name=name;obj.data.materials.clear();obj.data.materials.append(body.data.materials[regions.index(region)])
 for v in obj.data.vertices:
  co=obj.matrix_world@v.co
  if bone:weights=[(bone,1.)]
  else:
   _,idx,_=kd.find(co)
   weights=[(body.vertex_groups[g.group].name,g.weight) for g in body.data.vertices[idx].groups]
  for b,w in weights:
   group=obj.vertex_groups.get(b) or obj.vertex_groups.new(name=b);group.add([v.index],w,'REPLACE')
 for p in obj.data.polygons:p.use_smooth=True
 details.append(obj);return obj
def detail_sphere(name,center,scale,region,bone):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=6,location=center)
 obj=bpy.context.object;obj.scale=scale
 return detail_bind(obj,name,region,bone)
def project_front(x,z,offset=.3):
 hit,_,_,_=surface.ray_cast(Vector((x,-40,z)),Vector((0,1,0)),80)
 return Vector((x,hit.y-offset if hit is not None else -7,z))
# Eyes and mouth keep their original mesh and graphic treatment; no eyeballs/teeth.
# Fitted collar flaps with real thickness; bind each vertex to its local neck/torso influence.
for side in [-1,1]:
 points=[project_front(side*x,z,.35) for x,z in [(1.8,140),(5.8,141),(9.0,137),(4.2,133.5)]]
 mesh=bpy.data.meshes.new('Collar folded cloth');mesh.from_pydata(points,[],[(0,1,2,3)]);mesh.update()
 obj=bpy.data.objects.new('Collar',mesh);s.collection.objects.link(obj)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 solid=obj.modifiers.new('Cloth edge thickness','SOLIDIFY');solid.thickness=.30
 bpy.ops.object.modifier_apply(modifier=solid.name)
 detail_bind(obj,'Collar flap '+str(side),'Shirt')
# Raised cuff hems, with transverse rings rather than floating spheres.
if VARIANT!='runner':
 for side in [-1,1]:
  verts=[];faces=[]
  for j in range(3):
   for i in range(20):
    angle=i*math.tau/20
    point=Vector((side*(57+j*.45),3.5+4.25*math.cos(angle),137+3.5*math.sin(angle)))
    nearest,normal,_,_=surface.find_nearest(point)
    verts.append(nearest+normal*.25 if nearest is not None else point)
  for j in range(2):
   for i in range(20):faces.append((j*20+i,j*20+(i+1)%20,(j+1)*20+(i+1)%20,(j+1)*20+i))
  mesh=bpy.data.meshes.new('Cuff hem');mesh.from_pydata(verts,[],faces);mesh.update()
  obj=bpy.data.objects.new('Cuff',mesh);s.collection.objects.link(obj);detail_bind(obj,'Cuff edge '+str(side),'Shirt')
for z in [126,117,107,98]:
 pos=project_front(2.5,z,.25)
 detail_sphere('Shirt button',pos,(.43,.17,.43),'Leather','bip Spine1' if z>114 else 'bip Spine')
if VARIANT=='modern':
 verts=[];faces=[]
 for z,width in [(137,1.1),(134,1.8),(131,1.1),(125,1.3),(118,1.6),(111,1.9),(104,2.2),(100,0.15)]:
  for x in [-width,0,width]:verts.append(project_front(x,z,.60))
 for i in range(7):
  for j in range(2):faces.append((i*3+j,i*3+j+1,(i+1)*3+j+1,(i+1)*3+j))
 mesh=bpy.data.meshes.new('Simple tie');mesh.from_pydata(verts,[],faces);mesh.update()
 obj=bpy.data.objects.new('Simple tie',mesh);s.collection.objects.link(obj);detail_bind(obj,'Simple cloth tie','Tie')
bpy.ops.object.select_all(action='DESELECT')
for obj in details+[body]:obj.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
detail_report={'body_triangles_before':tri_before,'body_triangles_after':sum(len(p.vertices)-2 for p in body.data.polygons),'style':'Low Poly; original face retained, no added eyeballs or teeth','details':['moderate surface support','collar thickness','cuff hems','joint folds','knuckles','buttons'],'animation_curves_modified':False}

# Executed inside the baseline pipeline, in source centimetres / Blender Z-up.
# All additions are skinned and merged before the final UV/PBR bake.
parts=[]
from mathutils.bvhtree import BVHTree
surface=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(p.vertices) for p in body.data.polygons])
def finish_part(obj,name,region,bone):
 obj.name=name
 obj.data.materials.clear();obj.data.materials.append(body.data.materials[regions.index(region)])
 group=obj.vertex_groups.new(name=bone)
 group.add(list(range(len(obj.data.vertices))),1.,'REPLACE')
 for p in obj.data.polygons:p.use_smooth=True
 parts.append(obj)
 return obj
def ellipsoid(name,center,scale,region,bone,upper=False):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,location=center)
 obj=bpy.context.object
 if upper:
  bm=bmesh.new();bm.from_mesh(obj.data)
  bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z<-.001],context='VERTS')
  bm.to_mesh(obj.data);bm.free()
 obj.scale=scale
 return finish_part(obj,name,region,bone)
def box(name,center,size,region,bone):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center)
 obj=bpy.context.object;obj.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=obj.modifiers.new('Worn rounded edges','BEVEL');bevel.width=.35;bevel.segments=2
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 return finish_part(obj,name,region,bone)
if VARIANT=='miner':
 ellipsoid('Hard hat shell',(0,1,162),(11.5,12,11),'HardHat','bip Head',True)
 ellipsoid('Hard hat brim',(0,-.5,161.8),(14,14,.8),'HardHat','bip Head')
 box('Helmet ridge',(0,1,170.5),(2.5,15,2),'HardHat','bip Head')
 ellipsoid('Headlamp housing',(0,-12.2,165),(3.6,2.0,3.6),'Metal','bip Head')
 ellipsoid('Headlamp lens',(0,-13.9,165),(2.5,.35,2.5),'Lamp','bip Head')
 ellipsoid('Work belt',(0,1,87),(15,10,2),'Leather','bip Pelvis')
 box('Belt buckle',(0,-9,87),(4,1,3.5),'Metal','bip Pelvis')
 box('Left utility pouch',(16,1,85),(6,8,10),'Leather','bip Pelvis')
 box('Right utility pouch',(-16,1,85),(6,8,10),'Leather','bip Pelvis')
 for side,x in [('L',12.6),('R',-12.6)]:
  ellipsoid(side+' kneepad',(x,-5.5,53),(5.2,2.3,6.5),'Metal','bip '+side+' Calf')
 # Reflective chest strips follow source skin weights, including the spine blend.
 for x in [-8,8]:
  obj=box('Workwear reflective strip',(x,-10.3,120),(3,1,24),'Reflective','bip Spine1')
  for v in obj.data.vertices:
   co=obj.matrix_world@v.co
   hit,normal,face,distance=surface.ray_cast(Vector((co.x,-40,co.z)),Vector((0,1,0)),80)
   if hit is not None:
    co.y=hit.y-.22
    v.co=obj.matrix_world.inverted()@co
   near=min(body.data.vertices,key=lambda q:((body.matrix_world@q.co)-co).length_squared)
   for g in list(obj.vertex_groups):g.remove([v.index])
   for g in near.groups:
    name=body.vertex_groups[g.group].name
    group=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
    group.add([v.index],g.weight,'REPLACE')
else:
 # Surface injuries use the original skin itself, with no floating wound blobs.
 for p in body.data.polygons:
  co=sum((body.matrix_world@body.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
  shoulder=22<co.x<35 and co.y<2 and 132<co.z<143
  forearm=-58<co.x<-44 and co.y<1 and 132<co.z<142
  if shoulder or forearm:p.material_index=regions.index('DriedBlood')
if parts:
 bpy.ops.object.select_all(action='DESELECT')
 for obj in parts+[body]:obj.select_set(True)
 bpy.context.view_layer.objects.active=body
 bpy.ops.object.join()

bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.015,area_weight=.5);bpy.ops.object.mode_set(mode='OBJECT')

# Native Blender PBR baking: one game material, editable regions kept in .blend.
def node(nt,kind,name):
 n=nt.nodes.new(kind);n.name=name;n.label=name;return n
def ramp(nt,value,stops,name):
 n=node(nt,'ShaderNodeValToRGB',name);nt.links.new(value,n.inputs[0]);n.color_ramp.interpolation='EASE'
 for i,(position,color) in enumerate(stops):
  e=n.color_ramp.elements[i] if i<2 else n.color_ramp.elements.new(position);e.position=position;e.color=(*color,1)
 return n.outputs[0]
def noise(nt,vec,scale,name):
 n=node(nt,'ShaderNodeTexNoise',name);n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=3;nt.links.new(vec,n.inputs['Vector']);return n.outputs['Fac']
base={'Skin':((.075,.095,.075),(.30,.31,.22),.74),'Shirt':((.047,.057,.043),(.15,.155,.11),.94),'Trousers':((.018,.027,.033),(.07,.085,.087),.91),'Hair':((.008,.007,.006),(.044,.028,.017),.83),'Leather':((.008,.008,.007),(.035,.031,.024),.62),'DriedBlood':((.012,.003,.004),(.095,.022,.017),.69),'Eyes':((.018,.017,.012),(.1,.09,.058),.34)}
base.update({'HardHat':((.11,.068,.012),(.38,.25,.055),.65),'Reflective':((.22,.25,.18),(.52,.56,.39),.42),'Metal':((.012,.019,.023),(.045,.058,.06),.6),'Lamp':((.55,.42,.16),(.85,.75,.45),.27)})
if VARIANT=='miner':
 base.update({'Shirt':((.045,.017,.004),(.24,.09,.015),.93),'Trousers':((.012,.02,.028),(.042,.057,.072),.94),'Skin':((.035,.051,.044),(.20,.23,.17),.80)})
else:
 base.update({'Shirt':((.027,.006,.008),(.11,.035,.041),.95),'Trousers':((.014,.021,.026),(.05,.068,.079),.90),'Skin':((.10,.095,.068),(.38,.35,.25),.74),'DriedBlood':((.018,.002,.003),(.14,.018,.015),.63)})
base.update({'Tie':((.028,.007,.009),(.10,.025,.025),.87)})
# Reduce the broad speckled noise of V01; microdetail is added separately below.
base['Skin']=((.11,.125,.095),(.24,.265,.19),.78) if VARIANT!='runner' else ((.15,.14,.105),(.30,.29,.22),.77)
channels=[];materials=list(body.data.materials)
for region,mat in zip(regions,materials):
 mat.use_nodes=True;mat.use_fake_user=True;nt=mat.node_tree;nt.nodes.clear()
 bs=node(nt,'ShaderNodeBsdfPrincipled','Nonmetal surface');bs.inputs['Metallic'].default_value=0
 output=node(nt,'ShaderNodeOutputMaterial','Surface');nt.links.new(bs.outputs[0],output.inputs[0])
 coord=node(nt,'ShaderNodeTexCoord','Rest coordinates')
 coarse=noise(nt,coord.outputs['Object'],.15,'Irregular age and dirt')
 fine=noise(nt,coord.outputs['Object'],17 if region in ['Shirt','Trousers'] else 7,'Fabric or skin pores')
 lo,hi,rough=base[region];color=ramp(nt,coarse,[(.12,lo),(.88,hi)],'Muted material tones')
 nt.links.new(color,bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=rough
 bump=node(nt,'ShaderNodeBump','Fine surface relief');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.016 if region=='Skin' else .035
 nt.links.new(fine,bump.inputs['Height']);nt.links.new(bump.outputs[0],bs.inputs['Normal'])
 scalar=node(nt,'ShaderNodeValue','Roughness');scalar.outputs[0].default_value=rough
  # Evaluated in each semantic material, baked in rest-world centimetres.
 rough_output=scalar.outputs[0]
 geo=node(nt,'ShaderNodeNewGeometry','Anatomical rest position')
 def math_node(operation,a,b=None,name='Surface mask'):
  n=node(nt,'ShaderNodeMath',name);n.operation=operation
  if isinstance(a,(int,float)):n.inputs[0].default_value=a
  else:nt.links.new(a,n.inputs[0])
  if b is not None:
   if isinstance(b,(int,float)):n.inputs[1].default_value=b
   else:nt.links.new(b,n.inputs[1])
  return n.outputs[0]
 def patch(center,radius,label):
  sub=node(nt,'ShaderNodeVectorMath',label+' position');sub.operation='SUBTRACT';nt.links.new(geo.outputs['Position'],sub.inputs[0]);sub.inputs[1].default_value=center
  div=node(nt,'ShaderNodeVectorMath',label+' shape');div.operation='DIVIDE';nt.links.new(sub.outputs[0],div.inputs[0]);div.inputs[1].default_value=radius
  length=node(nt,'ShaderNodeVectorMath',label+' distance');length.operation='LENGTH';nt.links.new(div.outputs[0],length.inputs[0])
  edge=noise(nt,geo.outputs['Position'],1.7,label+' irregular edge')
  distance=math_node('ADD',length.outputs['Value'],math_node('MULTIPLY',edge,.23))
  fade=node(nt,'ShaderNodeMapRange',label+' feather');fade.interpolation_type='SMOOTHERSTEP';nt.links.new(distance,fade.inputs['Value'])
  fade.inputs['From Min'].default_value=.62;fade.inputs['From Max'].default_value=1.13;fade.inputs['To Min'].default_value=1;fade.inputs['To Max'].default_value=0
  return fade.outputs[0]
 def mix_color(factor,base_color,added,label):
  mix=node(nt,'ShaderNodeMixRGB',label);mix.blend_type='MIX';nt.links.new(factor,mix.inputs[0]);nt.links.new(base_color,mix.inputs[1]);mix.inputs[2].default_value=(*added,1)
  return mix.outputs[0]
 if region=='Skin':
  wound=patch((71,-.5,137),(4,4,1.8),'Hand abrasion')
  if VARIANT=='runner':
   wound=math_node('MAXIMUM',wound,patch((29,-1,137),(5.5,3,4.2),'Exposed shoulder injury'))
   wound=math_node('MAXIMUM',wound,patch((-49,-1.5,136),(5.0,3.5,2.0),'Forearm injury'))
  color=mix_color(wound,color,(.09,.012,.013),'Abraded skin')
  rough_output=math_node('SUBTRACT',rough_output,math_node('MULTIPLY',wound,.18))
  injury_bump=node(nt,'ShaderNodeBump','Shallow wound depression');injury_bump.invert=True;injury_bump.inputs['Distance'].default_value=.07;injury_bump.inputs['Strength'].default_value=.40
  nt.links.new(wound,injury_bump.inputs['Height']);nt.links.new(bump.outputs[0],injury_bump.inputs['Normal']);nt.links.new(injury_bump.outputs[0],bs.inputs['Normal'])
 if region in ['Shirt','Trousers']:
  # Crossed weave has lower relief than clothing folds in the mesh.
  weave=[]
  for axis in ['X','Z']:
   wv=node(nt,'ShaderNodeTexWave','Woven yarn '+axis);wv.wave_type='BANDS';wv.bands_direction=axis;wv.inputs['Scale'].default_value=22;wv.inputs['Distortion'].default_value=1.2;nt.links.new(coord.outputs['Object'],wv.inputs['Vector']);weave.append(wv.outputs['Fac'])
  yarn=math_node('MULTIPLY',weave[0],weave[1])
  weave_bump=node(nt,'ShaderNodeBump','Cloth weave relief');weave_bump.inputs['Distance'].default_value=.018;weave_bump.inputs['Strength'].default_value=.20
  nt.links.new(yarn,weave_bump.inputs['Height']);nt.links.new(bump.outputs[0],weave_bump.inputs['Normal']);nt.links.new(weave_bump.outputs[0],bs.inputs['Normal'])
  dirt=noise(nt,geo.outputs['Position'],.65,'Small irregular grime')
  color=mix_color(math_node('MULTIPLY',dirt,.22),color,(.012,.010,.008),'Embedded dust')
  stains=patch((10,-7,111),(4.5,5,12),'Chest blood stain') if region=='Shirt' else patch((-13,-3,51),(4.4,6,9),'Knee dirt')
  color=mix_color(math_node('MULTIPLY',stains,.75),color,(.065,.012,.009) if region=='Shirt' else (.024,.018,.011),'Irregular cloth staining')
 nt.links.new(color,bs.inputs['Base Color']);nt.links.new(rough_output,bs.inputs['Roughness'])

 channels.append((color,rough_output,bs,output))
textures=R/'textures';textures.mkdir(exist_ok=True)
s.render.engine='CYCLES';s.cycles.samples=4;s.cycles.device='CPU';s.render.bake.margin=12
images={}
for channel in ['albedo','roughness','normal']:
 im=bpy.data.images.new(VARIANT+'_'+channel,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if channel=='albedo' else 'Non-Color';images[channel]=im
 for mat,(color,rough,bs,out) in zip(materials,channels):
  nt=mat.node_tree;target=node(nt,'ShaderNodeTexImage','Bake '+channel);target.image=im
  for n in nt.nodes:n.select=False
  target.select=True;nt.nodes.active=target
  if channel=='normal':nt.links.new(bs.outputs[0],out.inputs[0])
  else:
   emission=node(nt,'ShaderNodeEmission','Bake source');nt.links.new(color if channel=='albedo' else rough,emission.inputs['Color']);nt.links.new(emission.outputs[0],out.inputs[0])
 bpy.ops.object.bake(type='NORMAL' if channel=='normal' else 'EMIT',normal_space='TANGENT')
 im.filepath_raw=str(textures/(channel+'.png'));im.file_format='PNG';im.save();im.pack()
for mat,(_,_,bs,out) in zip(materials,channels):mat.node_tree.links.new(bs.outputs[0],out.inputs[0])
game=bpy.data.materials.new(VARIANT+'_PBR');game.use_nodes=True;nt=game.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=0
for channel,im in images.items():
 tex=node(nt,'ShaderNodeTexImage',channel);tex.image=im
 if channel=='normal':
  nm=node(nt,'ShaderNodeNormalMap','Baked skin and clothing');nt.links.new(tex.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs['Normal'])
 else:nt.links.new(tex.outputs['Color'],bs.inputs['Base Color' if channel=='albedo' else 'Roughness'])
body.data.materials.clear();body.data.materials.append(game)
for poly in body.data.polygons:poly.material_index=0
body.name=VARIANT.title()+'Zombie'
head_center_world=Vector((0,-1,156))
head_offset=target_rest['bip Head'].inverted()@head_center_world
a.data.bones['bip Head'].name='head'
if 'bip Head' in body.vertex_groups:body.vertex_groups['bip Head'].name='head'
for act in bpy.data.actions:
 for fc in curves(act):fc.data_path=fc.data_path.replace('["bip Head"]','["head"]')
# Uniform meter conversion through a static root preserves every source curve.
root=bpy.data.objects.new('ModernZombieMeters',None);s.collection.objects.link(root)
for obj in [a,body]:
 if obj.parent is None:obj.parent=root
root.scale=(.01,.01,.01)
set_action(a,bpy.data.actions['Idle']);s.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for obj in [a,body,root]:obj.select_set(True)
bpy.context.view_layer.objects.active=a
bpy.ops.wm.save_as_mainfile(filepath=str(R/(VARIANT+'-zombie-v02.blend')))
bpy.ops.export_scene.gltf(filepath=str(R/(VARIANT+'-zombie-v02.glb')),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,export_force_sampling=True,export_frame_step=1,export_def_bones=False)
report={'source':'Denys Almaral ZombieMale_A; native zombie motions','donor':'Quaternius Universal Animation Library Death01 and Hit_Chest','bones':len(a.data.bones),'vertices':len(body.data.vertices),'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'clips':{act.name:(act.frame_range[1]-act.frame_range[0])/30 for act in bpy.data.actions},'retarget':retarget_report,'walk_reference_speed':walk_reference,'skin_weight_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices),'material_region_faces':{name:face_regions.count(i) for i,name in enumerate(regions)}}
report['head_hitbox_offset']=list(head_offset)
report['detail']=detail_report
(R/'build-report.json').write_text(json.dumps(report,indent=2));print('MODERN_ZOMBIE_BUILD_COMPLETE',json.dumps(report))
