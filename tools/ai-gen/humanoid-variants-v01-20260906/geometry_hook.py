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
    co.y=hit.y-.35+.2*(co.y+10.3)
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
