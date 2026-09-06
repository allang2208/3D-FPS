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
