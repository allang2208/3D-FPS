"""Author tailored ivory collar and restrained cross on the real female robe."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/ProductionR1';O=R/'Authored'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
d=read(R/'Inputs/native_robe.json')
bpy.ops.wm.open_mainfile(filepath=str(O/'Nun_Head_Hair.blend'))
tri=[t[::-1] for t,mat in zip(d['triangles'],d['triangle_materials']) if mat in (0,6)]
bvh=BVHTree.FromPolygons([Vector(p) for p in d['positions']],tri,all_triangles=True)
nh=read(R/'Inputs/native_head.json')
neck_bvh=BVHTree.FromPolygons([Vector(p) for p in nh['positions']],[t[::-1] for t,m in zip(nh['triangles'],nh['triangle_materials']) if m==0],all_triangles=True)
tree=KDTree(len(d['positions']))
for i,p in enumerate(d['positions']):tree.insert(p,i)
tree.balance()
def native_weights(p):
 accum={}
 for _,i,dist in tree.find_n(p,3):
  a=1/max(dist,.04)**2
  for b,w in d['weights'][i]:accum[int(b)]=accum.get(int(b),0)+a*w
 pairs=sorted(accum.items(),key=lambda x:-x[1])[:8];total=sum(v for _,v in pairs)
 return {d['bones'][k]['name']:v/total for k,v in pairs}
def mesh(name,p,f,uv=None):
 me=bpy.data.meshes.new(name);me.from_pydata(p,[],f);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for poly in me.polygons:poly.use_smooth=True
 if uv:
  layer=me.uv_layers.new(name='UVMap')
  for poly,tex in zip(me.polygons,uv):
   for li,xy in zip(poly.loop_indices,tex):layer.data[li].uv=xy
 return ob
def cloth_mat(name,color):
 mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True
 sh=mat.node_tree.nodes.get('Principled BSDF');sh.inputs['Base Color'].default_value=(*color,1);sh.inputs['Roughness'].default_value=.88;sh.inputs['Sheen Weight'].default_value=.2
 return mat
black=cloth_mat('Nun_Black_Wool',(.018,.017,.016));ivory=cloth_mat('Nun_Ivory_Linen',(.68,.65,.57));iron=cloth_mat('Nun_Worn_Iron',(.12,.105,.09));iron.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value=.85
robe=mesh('Nun_Robe_Reference',d['positions'],[t[::-1] for t in d['triangles']],[[[a,1-b] for a,b in tex[::-1]] for tex in d['uv']]);robe.data.materials.append(black)
# Real 2.5 mm cloth around the neck, following the outer robe at every angle.
ps=[];faces=[];uvs=[];N=128;M=12
for row in range(M+1):
 u=row/M
 for col in range(N):
  angle=math.tau*col/N;front=max(0,math.cos(angle));z=143.1-u*(4.7+2.2*front)
  direction=Vector((math.sin(angle),math.cos(angle),0));start=Vector((0,1.3,z))
  hit,n,idx,dist=bvh.ray_cast(start,direction,40)
  if hit is None:hit,n,idx,dist=neck_bvh.ray_cast(start,direction,40)
  if hit is None:raise RuntimeError('Collar needs real neck surface at '+str((row,col)))
  point=hit+direction*(.25+.10*math.sin(u*math.pi))
  ps.append(tuple(point))
for row in range(M):
 for col in range(N):
  j=(col+1)%N;faces.append((row*N+col,row*N+j,(row+1)*N+j,(row+1)*N+col));uvs.append([(col/N,row/M),((col+1)/N,row/M),((col+1)/N,(row+1)/M),(col/N,(row+1)/M)])
collar=mesh('Nun_Ivory_Collar',ps,faces,uvs);collar.data.materials.append(ivory)
bpy.context.view_layer.objects.active=collar
solid=collar.modifiers.new('SewnThickness','SOLIDIFY');solid.thickness=.25;solid.offset=0
bpy.ops.object.modifier_apply(modifier=solid.name)
parts=[collar]
def front(x,z,offset=.35):
 hit,normal,i,dist=bvh.ray_cast(Vector((x,40,z)),Vector((0,-1,0)),65)
 if hit is None:raise RuntimeError('Necklace needs chest surface')
 return hit+Vector((0,offset,0))
path=[]
for i in range(61):
 t=i/60;x=-4.3+8.6*t;z=128.2+12.2*(abs(t-.5)*2)**1.35;path.append(front(x,z,.42))
cu=bpy.data.curves.new('Nun_Cord','CURVE');cu.dimensions='3D';cu.bevel_depth=.065;cu.bevel_resolution=2
sp=cu.splines.new('POLY');sp.points.add(len(path)-1)
sp.points.foreach_set('co',[v for p in path for v in (*p,1)])
ob=bpy.data.objects.new('Nun_Cord',cu);bpy.context.collection.objects.link(ob);ob.data.materials.append(black)
bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.ops.object.convert(target='MESH');parts.append(bpy.context.object)
c=front(0,126.4,.62)
for name,offset,size in [('CrossStem',(0,0,0),(.42,.22,4.3)),('CrossArm',(0,0,.65),(2.8,.22,.42))]:
 bpy.ops.mesh.primitive_cube_add(size=1,location=c+Vector(offset));ob=bpy.context.object;ob.name='Nun_'+name;ob.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=ob.modifiers.new('SoftMachinedEdges','BEVEL');bevel.width=.065;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name);ob.data.materials.append(iron);parts.append(ob)
# One skinned trim mesh; hardware is bound to the same torso as its support.
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=collar;bpy.ops.object.join();trim=bpy.context.object;trim.name='SK_Nun_Collar_Cross'
for ob in (trim,robe):
 for b in d['bones']:ob.vertex_groups.new(name=b['name'])
 for i,v in enumerate(ob.data.vertices):
  ws=native_weights(ob.matrix_world@v.co) if ob==trim else {d['bones'][k]['name']:w for k,w in d['weights'][i]}
  for name,w in ws.items():ob.vertex_groups[name].add([i],w,'REPLACE')
# Explicit UVs on the small hardware use centimetre-scaled local coordinates.
if not trim.data.uv_layers.active:trim.data.uv_layers.new(name='UVMap')
trim.data.calc_loop_triangles()
out=dict(binding_source=d['source'],bones=d['bones'],positions=[list(trim.matrix_world@v.co) for v in trim.data.vertices],weights=[[[g.group,g.weight] for g in v.groups] for v in trim.data.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=['IvoryLinen','BlackCord','WornIron'])
mapping={mat.name:i for i,mat in enumerate([ivory,black,iron])}
for t in trim.data.loop_triangles:
 order=list(t.loops)[::-1];out['triangles'].append(list(t.vertices)[::-1]);out['uv'].append([[trim.data.uv_layers.active.data[i].uv.x,1-trim.data.uv_layers.active.data[i].uv.y] for i in order]);out['normals'].append([list(trim.data.vertices[trim.data.loops[i].vertex_index].normal) for i in order]);out['triangle_materials'].append(mapping[trim.data.materials[t.material_index].name])
(O/'trim.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
# Keep a named editable native armature with the same reference transforms.
from mathutils import Matrix
arm=bpy.data.armatures.new('Kaitlin_Nun_Rig');rig=bpy.data.objects.new('Kaitlin_Nun_Rig',arm);bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
head=read(R/'Inputs/native_head.json');bone_specs={b['name']:b for b in d['bones']}
bone_specs.update({b['name']:b for b in head['bones']})
created={}
for name,b in bone_specs.items():
 bone=arm.edit_bones.new(name);bone.head=b['position'];bone.tail=Vector(b['position'])+Vector(b['axes'][0]);bone.align_roll(Vector(b['axes'][2]));created[name]=bone
for source in (d,head):
 for b in source['bones']:
  if b['parent']>=0:created[b['name']].parent=created[source['bones'][b['parent']]['name']]
bpy.ops.object.mode_set(mode='OBJECT')
for ob in (robe,trim,bpy.data.objects['SK_NunHead']):
 mod=ob.modifiers.new('NativeBinding','ARMATURE');mod.object=rig;ob.parent=rig
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ChapelNun_Complete_Source.blend'))
(O/'garment_receipt.json').write_text(json.dumps(dict(trim='trim.json',blend='ChapelNun_Complete_Source.blend',robe_source=d['source'],collar_thickness_cm=.25,physics='Existing continuous skirt Chaos asset will be duplicated with the female collision envelope; separate cuff inertia material',tested=False),indent=2),encoding='utf-8')
print('NUN_COLLAR_CROSS_SOURCE_SAVED',flush=True)
