import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'HK416CommonAttachments20260930'));import reargrip_interfaces as R
bpy.context.preferences.filepaths.save_version=0
out=O/'Meshes';out.mkdir(exist_ok=True);report={'parts':{},'runtime_tested':False}
native_sections=json.loads((O/'native_sections.json').read_text())
original_section=R.section
def closed_donor_section(mesh,z,count=256):
 # The refined donors contain separate open texture shells. Build the mounting
 # shoulder from their outer section hull, closing only this new cut interface.
 from mathutils.geometry import convex_hull_2d
 points=[]
 for f in mesh.polygons:
  ids=list(f.vertices)
  for j,i in enumerate(ids):
   a=mesh.vertices[i].co;b=mesh.vertices[ids[(j+1)%len(ids)]].co
   if (a.z-z)*(b.z-z)<0:points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
 points=[points[i] for i in convex_hull_2d([p.xy for p in points])];center=sum(points,Vector())/len(points);outline=[]
 cross=lambda a,b:a.x*b.y-a.y*b.x
 for j in range(count):
  d=Vector((math.cos(math.tau*j/count),math.sin(math.tau*j/count)));dist=[]
  for pa,pb in zip(points,points[1:]+points[:1]):
   a=pa.xy-center.xy;e=pb.xy-pa.xy;den=cross(d,e)
   if abs(den)<1e-12:continue
   t=cross(a,e)/den;u=cross(a,d)/den
   if -.000001<=u<=1.000001 and t>0:dist.append(t)
  if not dist:raise RuntimeError('Invalid donor outer shoulder')
  p=center.xy+d*max(dist);outline.append(Vector((p.x,p.y,z)))
 return outline
for key,cut in [('phantom_reargrip',0.),('stable_antislip_reargrip',-.012),('balanced_reargrip',-.003)]:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')),use_anim=False)
 body=next(o for o in bpy.context.scene.objects if o.type=='MESH');body.data.transform(body.matrix_world);body.parent=None;body.matrix_world=Matrix.Identity(4)
 # Remove the old rifle-specific collar. Preserve the accepted body, UVs, colors and authored normals.
 R.remember_normals(body.data);bm=bmesh.new();bm.from_mesh(body.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES');bm.to_mesh(body.data);bm.free();R.restore_normals(body.data)
 body.data.materials[0].name='S90_CommonBody';body.data.materials.pop(index=1)
 # Align two centreline stations in the hold region with the native grip using a rigid transform.
 def station(z):
  points=[]
  for f in body.data.polygons:
   ids=list(f.vertices)
   for j,i in enumerate(ids):
    a=body.data.vertices[i].co;b=body.data.vertices[ids[(j+1)%len(ids)]].co
    if (a.z-z)*(b.z-z)<0:points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
  if not points:raise RuntimeError('Missing donor centreline station')
  return Vector([(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)])
 a=station(-.030);b=station(-.055)
 na=Vector(native_sections['-0.84']['center']);nb=Vector(native_sections['-0.86']['center'])
 flip=Matrix.Rotation(math.pi,4,'Z');aa=flip@a;bb=flip@b
 rotation=(bb-aa).rotation_difference(nb-na).to_matrix().to_4x4()@flip
 target=(na+nb)*.5;shift=target-rotation@((a+b)*.5);transform=Matrix.Translation(shift)@rotation
 # Cut below the native grip's bifurcating upper web, retaining that whole web.
 # Both cut planes use component space; the accepted donor body remains rigid.
 body.data.transform(transform);native_cut=-.823;cut=-.836
 print('GRAFT_STATIONS',key,cut,native_cut,flush=True)
 # The interface helper retains the original upper contact surface and authors only the transition.
 native_file=O/'Inputs/native_grip.blend'
 R.CUT[key]=cut;R.NATIVE_CUT=native_cut
 R.section=lambda mesh,z,count=256:closed_donor_section(mesh,z,count) if mesh==body.data else original_section(mesh,z,count)
 mat=bpy.data.materials.new('S90_NativeInterface')
 neck,fit=R.fit_reargrip(key,body,Matrix.Identity(4),native_file,mat)
 # The preserved native UV area and the newly generated neck have distinct surface inputs.
 native_neck=bpy.data.materials.new('S90_TransitionPolymer');neck.data.materials.append(native_neck)
 for f in neck.data.polygons:
  if any(neck.data.vertices[i].co.z<native_cut-1e-6 for i in f.vertices):f.material_index=1
 for i,layer in enumerate(neck.data.uv_layers):
  if i<len(body.data.uv_layers):layer.name=body.data.uv_layers[i].name
 fit['native_contact']='Unchanged native component-space surface above Z=-82.3 cm'
 fit['lower_body_transform']='Rigid centreline fit; no body scaling'
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);neck.select_set(True);bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
 body.name='SM_Super90_'+key;body.data.uv_layers.active_index=0;body.data.uv_layers[0].active_render=True
 # Preserve source shading; repair only collapsed cut/source microfaces and UVs
 # that cannot produce a tangent when the new static mesh is imported.
 R.remember_normals(body.data);bm=bmesh.new();bm.from_mesh(body.data)
 invalid=[f for f in bm.faces if f.calc_area()<1e-14];removed=len(invalid)
 if invalid:bmesh.ops.delete(bm,geom=invalid,context='FACES')
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(body.data);bm.free();R.restore_normals(body.data)
 fixed_uv=0;uv=body.data.uv_layers[0].data
 for f in body.data.polygons:
  p=[uv[i].uv.copy() for i in f.loop_indices]
  if abs((p[1]-p[0]).cross(p[2]-p[0]))>1e-10:continue
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(f.normal[i]))]
  for li in f.loop_indices:
   co=body.data.vertices[body.data.loops[li].vertex_index].co;uv[li].uv=(co[axes[0]]/.04,co[axes[1]]/.04)
  fixed_uv+=1
 file=out/(body.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.data.libraries.write(str(file.with_suffix('.blend')),{body},fake_user=True)
 body.data.calc_loop_triangles();areas={}
 for t in body.data.loop_triangles:
  uv=body.data.uv_layers[0].data;p=[uv[i].uv for i in t.loops];uvarea=abs((p[1]-p[0]).cross(p[2]-p[0]))*.5
  entry=areas.setdefault(t.material_index,[0.,0.]);entry[0]+=t.area*10000;entry[1]+=uvarea
 report['parts'][key]={'file':str(file),'triangles':len(body.data.loop_triangles),'slots':[m.name for m in body.data.materials],'fit':fit,'rigid_transform':[list(r) for r in transform],'area_cm2_uv':areas,'removed_zero_area_faces':removed,'repaired_collapsed_uv_faces':fixed_uv}
 print('SUPER90_REARGRIP_AUTHORED',key,report['parts'][key],flush=True)
(O/'models.json').write_text(json.dumps(report,indent=2))
