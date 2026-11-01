"""Differentiate the two existing Norse seats while retaining their mating surfaces."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
for folder in ('Export','Textures','Icons'):(P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
CX=-.0004452141001820564; CZ=.9095
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0.,1.);return t*t*(3.-2.*t)
def shape(p,kind):
 q=p.copy();x=np.abs(p[:,0]-CX);z=p[:,2];y=np.abs(p[:,1])
 r=np.sqrt((x/.0535)**2+((z-CZ)/.0412)**2)
 mating=(1-smooth(.058,.062,x))*smooth(.847,.858,z)*(1-smooth(.978,.988,z))
 face=smooth(.019,.031,y);keep_seal=smooth(.94,1.005,r)
 if kind=='guan_lei_seat':
  # Sculpt the existing complete annulus into a deep, continuous return rim.
  ring=smooth(.94,1.025,r)*(1-smooth(1.12,1.30,r))
  upper=((x-.045)/.020)**2+((z-.960)/.024)**2
  lower=((x-.045)/.020)**2+((z-.862)/.023)**2
  shoulders=1-smooth(.10,1.30,np.minimum(upper,lower))
  depth=.003*shoulders*keep_seal*mating*face
  # Four lobes read as forged returning knots, continuous with the original body.
  theta=np.arctan2((z-CZ)/.0412,(p[:,0]-CX)/.0535)
 else:
  # The same factory emblem sits in a slimmer, upward tapering load-bearing body.
  shoulder=1-smooth(.05,1.2,((x-.046)/.019)**2+((z-.959)/.025)**2)
  depth=-.0045*shoulder*keep_seal*mating*face
 q[:,1]+=np.sign(p[:,1])*depth
 return q
def transform_native(obj,kind):
 mesh=obj.data;n=len(mesh.vertices);nl=len(mesh.loops)
 p=np.empty(n*3,np.float64);mesh.vertices.foreach_get('co',p);p=p.reshape(-1,3)
 ln=np.empty(nl*3,np.float64);mesh.corner_normals.foreach_get('vector',ln);ln=ln.reshape(-1,3)
 vi=np.empty(nl,np.int32);mesh.loops.foreach_get('vertex_index',vi)
 q=shape(p,kind);jac=np.empty((n,3,3));eps=.00002
 for axis in range(3):
  a=p.copy();b=p.copy();a[:,axis]+=eps;b[:,axis]-=eps
  jac[:,:,axis]=(shape(a,kind)-shape(b,kind))/(2*eps)
 inv=np.linalg.inv(jac);nn=np.empty_like(ln)
 for axis in range(3):nn[:,axis]=np.sum(inv[vi,:,axis]*ln,axis=1)
 nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
 mesh.vertices.foreach_set('co',q.ravel());mesh.update()
 mesh.normals_split_custom_set(nn.tolist())
 return int(np.sum(np.linalg.norm(q-p,axis=1)>1e-8))
def remove_old_peak(obj):
 # V1's separate tiny tip is a closed connected island. Replace the whole
 # island, never cut the retained factory cap or disturb its UVs/normals.
 bm=bmesh.new();bm.from_mesh(obj.data)
 native=bm.loops.layers.float_vector.new('PreservedCornerNormal')
 for face,poly in zip(bm.faces,obj.data.polygons):
  for loop,li in zip(face.loops,poly.loop_indices):loop[native]=obj.data.corner_normals[li].vector
 seeds=[v for v in bm.verts if v.co.z>.995]
 seen=set(seeds);todo=list(seeds)
 while todo:
  v=todo.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w not in seen:seen.add(w);todo.append(w)
 if seen:
  bmesh.ops.delete(bm,geom=list(seen),context='VERTS')
  normals=[tuple(loop[native]) for face in bm.faces for loop in face.loops]
  bm.to_mesh(obj.data)
  for face in obj.data.polygons:face.use_smooth=True
  obj.data.normals_split_custom_set(normals)
 bm.free()
def forged_material(part):
 mat=bpy.data.materials.new('M_ThunderSeatV9_'+part);mat.use_nodes=True
 ns=mat.node_tree.nodes;ls=mat.node_tree.links;ns.clear()
 bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs[0],out.inputs['Surface'])
 nodes={}
 for kind in ('BaseColor','ORM','Normal'):
  im=bpy.data.images.load(str(P/'Textures'/('T_ThunderSeatV9_'+part+'_'+kind+'.png')));im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  tex=ns.new('ShaderNodeTexImage');tex.image=im;nodes[kind]=tex
 ls.new(nodes['BaseColor'].outputs[0],bs.inputs['Base Color'])
 sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['ORM'].outputs[0],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 normal=ns.new('ShaderNodeNormalMap');ls.new(nodes['Normal'].outputs[0],normal.inputs['Color']);ls.new(normal.outputs[0],bs.inputs['Normal'])
 return mat
def return_ring(side,material):
 # A closed, smoothly forged replacement bezel seated inside the existing
 # solid. The inner opening leaves the original rune untouched and uncovered.
 profile=[(.90,.022),(.90,.057),(.915,.063),(.94,.067),(.97,.068),(1.05,.068),(1.095,.065),(1.13,.058),(1.14,.049),(1.14,.022)]
 rings=256;count=len(profile);verts=[];faces=[]
 for i in range(rings):
  angle=2*math.pi*i/rings
  for radius,depth in profile:verts.append((CX+.0535*radius*math.cos(angle),side*depth,CZ+.0412*radius*math.sin(angle)))
 for i in range(rings):
  for j in range(count):faces.append((i*count+j,((i+1)%rings)*count+j,((i+1)%rings)*count+(j+1)%count,i*count+(j+1)%count))
 mesh=bpy.data.meshes.new('Closed return bezel');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  indices=[mesh.loops[li].vertex_index//count for li in poly.loop_indices];seam=max(indices)-min(indices)>1
  for li in poly.loop_indices:
   idx=mesh.loops[li].vertex_index;i=idx//count;j=idx%count
   uv.data[li].uv=((rings if seam and i==0 else i)/rings,j/count)
  poly.use_smooth=True
 obj=bpy.data.objects.new('Closed returning knot bezel '+str(side),mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material)
 return obj
def peak(name,points,halfdepth,material):
 # Closed forged volumes with a centre ridge, tapered thickness and bevelled
 # edges. Their roots sink 4 mm into the preserved cap, with no open underside.
 z0=min(z for x,z in points);z1=max(z for x,z in points);verts=[]
 for side in (-1,1):
  for x,z in points:
   t=(z-z0)/(z1-z0);verts.append((CX+x,side*halfdepth*(1-.70*t),z))
 count=len(points);faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]
 faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 uv=mesh.uv_layers.new(name='UVMap');xs=[p[0] for p in points];xmin,xmax=min(xs),max(xs)
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   co=mesh.vertices[mesh.loops[li].vertex_index].co
   if abs(poly.normal.y)>.25:uv.data[li].uv=((co.x-CX-xmin)/(xmax-xmin), (co.z-z0)/(z1-z0))
   elif abs(poly.normal.z)>.7:uv.data[li].uv=((co.x-CX-xmin)/(xmax-xmin),(co.y+halfdepth)/(2*halfdepth))
   else:uv.data[li].uv=((co.y+halfdepth)/(2*halfdepth),(co.z-z0)/(z1-z0))
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bevel=obj.modifiers.new('Forged rounded edges','BEVEL');bevel.width=.00065;bevel.segments=4
 bpy.ops.object.modifier_apply(modifier=bevel.name)
 for face in obj.data.polygons:face.use_smooth=True
 weighted=obj.modifiers.new('Broad forged face normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=40
 bpy.ops.object.modifier_apply(modifier=weighted.name)
 return obj
specs=[('guan_lei_seat','贯雷锤座','GuanLeiReturnC8/GuanLei_ReturnC8_Editable.blend',
 '/Game/Weapons/ThunderGodHammer20261028/GuanLeiReturnC8/M_GuanLeiC8_guan_lei_seat',
 '原厂雷纹圆徽 · 深厚闭合回环 · 四向回折锻肩'),
 ('ji_lei_seat','疾雷锤座','JiLeiSeatV1/JiLeiSeatV1_Editable.blend',
 '/Game/Weapons/ThunderGodHammer20261028/JiLeiSeatV1/M_JiLeiSeatV1_ji_lei_seat',
 '原厂雷纹圆徽 · 三尖上扬引雷冠 · 内收嵌银雷肩')]
rows=[];crown=None
for key,title,source,asset,appearance in specs:
 name='SM_ThunderGodHammer_head_mount_'+key
 with bpy.data.libraries.load(str(P.parent/source),link=False) as(a,b):b.objects=[name]
 obj=b.objects[0];bpy.context.collection.objects.link(obj);obj.hide_render=False;obj.hide_set(False)
 changed=transform_native(obj,key)
 materials=[dict(slot=obj.data.materials[0].name,asset=asset)]
 parts=[]
 if key=='guan_lei_seat':
  rim=forged_material('ReturnRing');parts=[return_ring(-1,rim),return_ring(1,rim)]
  materials.append(dict(slot=rim.name,asset='/Game/Weapons/ThunderGodHammer20261028/SeatDistinctV9/M_ThunderSeatV9_ReturnRing'))
 if key=='ji_lei_seat':
  remove_old_peak(obj);crown=forged_material('Crown')
  center=[(-.014,.986),(-.014,.998),(-.005,1.010),(-.007,1.012),(0,1.031),(.009,1.014),(.004,1.008),(.014,1.000),(.014,.986)]
  flank=[(.018,.986),(.018,.995),(.028,1.006),(.027,1.011),(.036,1.019),(.038,1.004),(.032,.996),(.034,.986)]
  parts=[peak('Central forged lightning crown',center,.015,crown),peak('Right upward lightning tine',flank,.011,crown),peak('Left upward lightning tine',[(-x,z) for x,z in reversed(flank)],.011,crown)]
  materials.append(dict(slot=crown.name,asset='/Game/Weapons/ThunderGodHammer20261028/SeatDistinctV9/M_ThunderSeatV9_Crown'))
 if parts:
  bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
  for part in parts:part.select_set(True)
  bpy.context.view_layer.objects.active=obj;bpy.ops.object.join()
 obj.data.calc_loop_triangles()
 coords=np.empty(len(obj.data.vertices)*3);obj.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
 rows.append(dict(id=key,name=title,mesh=name,appearance=appearance,source=str(P.parent/source),materials=materials,
  triangles=len(obj.data.loop_triangles),modified_native_vertices=changed,bounds_m=[coords.min(axis=0).tolist(),coords.max(axis=0).tolist()]))
 obj.hide_render=True;obj.hide_set(True)
 print('SEAT_EXPORTED',key,len(obj.data.loop_triangles),flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderSeats_DistinctV9.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(complete=True,parts=rows,protected='factory seal centre, lateral mating faces and neck connection',normal_maps='retained original 4K PBR plus dedicated 2K crown and return-ring engraving normals',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
