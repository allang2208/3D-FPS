"""416 furniture on the existing QBZ stock shoulder and factory grip interface.
Production only: source UV0 retained, no rendering or acceptance tests.
"""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;H=S/'HK416Reworked20260930'
I=json.loads((H/'authoring.json').read_text());R=Matrix(I['root_matrix']);A=Matrix(I['source_to_weapon_root'])
bpy.context.preferences.filepaths.save_version=0
report={'parts':{},'source':'HK416 Full ReWorked by MojoLeeDa; CC BY 4.0','testing':'Not run'}
adapter_material=None
def append(file,name):
 with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
 ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.hide_set(False)
 ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear();ob.vertex_groups.clear()
 return ob
def active(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
def cap(ob,z,upper):
 bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
 bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-6 for v in e.verts)],sides=0)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
def box(name,center,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.scale=size
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bevel=ob.modifiers.new('Receiver edge radius','BEVEL');bevel.width=.0005;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
 ob.data.materials.append(adapter_material);return ob
def palm_center(ob):
 # Intersect the actual surface at palm height: a low-poly grip can have long
 # edges across this slice without any vertices inside a narrow Z interval.
 points=[];z=-.035
 for edge in ob.data.edges:
  a,b=[ob.data.vertices[i].co for i in edge.vertices]
  if (a.z-z)*(b.z-z)<=0 and abs(b.z-a.z)>1e-8:points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
 return Vector([(min(v[i] for v in points)+max(v[i] for v in points))*.5 for i in (0,1)]+[0])
def uv_layers(ob):
 coords=[tuple(x.uv) for x in ob.data.uv_layers[0].data] if ob.data.uv_layers else None
 for layer in list(ob.data.uv_layers):ob.data.uv_layers.remove(layer)
 first=ob.data.uv_layers.new(name='SourceUV0');coat=ob.data.uv_layers.new(name='ReceiverUV1')
 for poly in ob.data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(poly.normal[k]))]
  for li in poly.loop_indices:
   point=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv=(point[axes[0]]/.1,point[axes[1]]/.1)
   first.data[li].uv=coords[li] if coords else uv;coat.data[li].uv=uv
 ob.data.uv_layers.active_index=0;first.active_render=True
for part,key in [('stock','factory_stock'),('reargrip','factory_grip')]:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 adapter_material=bpy.data.materials.new('QBZ416_AdapterMetal')
 ob=append(H/'Exports/Attachments'/('SM_HK416_'+key+'_Editable.blend'),'SM_HK416_'+key)
 ob.data.transform(R.inverted());extras=[]
 if part=='stock':
  source=A@Vector((0,-.0385,.01945));target=Vector((.000688,.065,.0615))
  ob.data.transform(Matrix.Translation(target-source))
  extras=[box('QBZ receiver cap',(.000688,.0585,.0615),(.034,.014,.042)),box('QBZ shoulder',(.000688,.0645,.0615),(.029,.006,.033))]
  fit={'source_shoulder':list(source),'target_shoulder':list(target),'physical_scale':1.0,'adapter':'same receiver cap and shoulder as accepted QBZ tactical stock'}
 else:
  refdir=S/'PhantomRearGripSeamFit20260913'
  m4=append(refdir/'M4_Assembly_Editable.blend','FactoryMountReference')
  qbz=append(refdir/'QBZ191_Assembly_Editable.blend','FactoryMountReference')
  delta=palm_center(qbz)-palm_center(m4);ob.data.transform(Matrix.Translation(delta))
  bpy.data.objects.remove(m4,do_unlink=True)
  # Keep the receiver's actual top surface. The overlap is inside the grip;
  # both pieces are capped so the interface has no exposed hollow cut.
  cap(ob,.012,False);cap(qbz,.009,True)
  head=[v.co for v in ob.data.vertices if .009<=v.co.z<=.0121]
  lo=[min(v[i] for v in head) for i in (0,1)];hi=[max(v[i] for v in head) for i in (0,1)]
  for v in qbz.data.vertices:
   t=max(0,min(1,(.015-v.co.z)/.006));t=t*t*(3-2*t)
   for axis in (0,1):v.co[axis]=v.co[axis]*(1-t)+max(lo[axis]+.0005,min(hi[axis]-.0005,v.co[axis]))*t
  qbz.data.materials.clear();qbz.data.materials.append(adapter_material);extras=[qbz]
  fit={'palm_slice_z':-.035,'grip_translation':list(delta),'source_grip_cap_z':.012,'factory_neck_cap_z':.009,'physical_scale':1.0}
 for obj in [ob]+extras:obj.data.update();uv_layers(obj)
 active(ob)
 if part=='reargrip':
  # Unite the closed overlap into one continuous neck, retaining face UVs and
  # material identity instead of leaving coincident internal cap surfaces.
  union=ob.modifiers.new('Factory neck transition','BOOLEAN');union.operation='UNION';union.solver='EXACT';union.material_mode='TRANSFER';union.object=extras[0]
  bpy.ops.object.modifier_apply(modifier=union.name);bpy.data.objects.remove(extras[0],do_unlink=True)
 else:
  for extra in extras:extra.select_set(True)
  bpy.ops.object.join()
 ob.name='SM_416_Stock' if part=='stock' else 'SM_416_RearGrip'
 out=O/'QBZ191';out.mkdir(exist_ok=True);file=out/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.data.libraries.write(str(out/(ob.name+'_Editable.blend')),{ob},fake_user=True)
 report['parts'][part]={'name':ob.name,'family':'QBZ191','source_key':key,'fbx':str(file),'fit':fit,'slots':[m.name for m in ob.data.materials]}
(O/'models.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('416_QBZ_MODELS_AUTHORED',len(report['parts']),flush=True)
