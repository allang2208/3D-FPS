"""Three native-seat structural revisions; immutable medallion and mating faces."""
from pathlib import Path
import bpy,bmesh,numpy as np,json
P=Path(__file__).resolve().parent
CX=-.0004452141;CZ=.9095
IDS=('reinforced_block','ribbed_light','laminated_damper')
APPEARANCE={
 'reinforced_block':'原厂三结圆徽 · 双阶厚壁锻肩 · 加厚顶沿',
 'ribbed_light':'原厂三结圆徽 · 双侧贯穿减重窗 · 连续承力锻肋',
 'laminated_damper':'原厂三结圆徽 · 三阶锻钢叠层 · 双道内嵌缓冲层'}
(P/'Export').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'SeatInlaidC6/ThorSeats_InlaidC6.blend'),link=False) as(a,b):
 b.objects=['SM_ThunderGodHammer_head_mount_'+k for k in IDS]
sources=dict(zip(IDS,b.objects))

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0.,1.);return t*t*(3.-2.*t)

def region(p):
 x=np.abs(p[:,0]-CX);z=p[:,2];y=np.abs(p[:,1])
 r=np.sqrt((x/.0535)**2+((z-CZ)/.0412)**2)
 # Exact source end rings and original seal remain untouched.
 protect=(1.-smooth(.0598,.0640,x))*smooth(.846,.851,z)*smooth(1.045,1.145,r)
 shoulder=smooth(.028,.036,x)*smooth(.943,.951,z)*(1.-smooth(.975,.980,z))
 return x,z,protect*shoulder*smooth(.017,.027,y)

def seam_weight(z):
 d=np.minimum(abs(z-.9593),abs(z-.9690))
 return 1.-smooth(.00115,.00205,d)

def deform(p,key):
 out=p.copy();x,z,w=region(p);side=np.where(p[:,1]<0.,-1.,1.)
 if key=='reinforced_block':
  # A broad terrace, a second raised terrace and a slightly raised native cap.
  terrace=smooth(.0415,.0435,x)*smooth(.950,.952,z)
  lower=smooth(.030,.038,x)*(1.-smooth(.0598,.0640,x))*smooth(.851,.856,z)*(1.-smooth(.875,.881,z))
  r=np.sqrt((x/.0535)**2+((z-CZ)/.0412)**2)
  lower*=smooth(1.045,1.145,r)*smooth(.017,.027,abs(p[:,1]))
  out[:,1]+=side*(w*(.0045+.0032*terrace)+lower*.0048)
  cap=smooth(.977,.983,z)*(1.-smooth(.0598,.0640,x))
  out[:,2]+=.0035*cap
 elif key=='laminated_damper':
  seam=seam_weight(z)
  # Three raised steel lands, with two 2.3 mm wide dark recessed layers.
  land=.0048+.0014*smooth(.9698,.972,z)
  out[:,1]+=side*w*(land-.0080*seam)
  # Recess also turns around each shoulder, making layers legible obliquely.
  out[:,0]-=np.sign(p[:,0]-CX)*w*.0025*seam
 elif key=='ribbed_light':
  out[:,1]-=side*w*.0008
 return out

def material(name,color,metal,rough):
 mat=bpy.data.materials.new(name);mat.use_nodes=True
 bs=mat.node_tree.nodes.get('Principled BSDF')
 bs.inputs['Base Color'].default_value=(*color,1.)
 bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
 return mat
inner=material('M_ThorSeatV7_InnerSteel',(.085,.09,.095),.92,.43)
buffer=material('M_ThorSeatV7_Buffer',(.016,.017,.018),.05,.76)

def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False)
 ob.select_set(True);bpy.context.view_layer.objects.active=ob

def cutter(side):
 # A chamfered oblique triangular aperture entirely outside the native seal.
 outline=np.array([(.034,.9692),(.0527,.9678),(.0556,.9649),(.0554,.9502),(.0527,.9501),(.0370,.9655)])
 center=outline.mean(axis=0);verts=[]
 sections=[(-.090,1.08),(-.045,1.08),(-.031,1.),(.031,1.),(.045,1.08),(.090,1.08)]
 for y,scale in sections:
  q=center+(outline-center)*scale
  verts.extend((CX+side*x,y,z) for x,z in q)
 n=len(outline);faces=[tuple(range(n-1,-1,-1)),tuple((len(sections)-1)*n+i for i in range(n))]
 for j in range(len(sections)-1):
  for i in range(n):
   k=(i+1)%n;faces.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
 mesh=bpy.data.meshes.new('WindowConstruction');mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 ob=bpy.data.objects.new('Aperture_'+str(side),mesh);bpy.context.collection.objects.link(ob)
 return ob

rows=[]
for key in IDS:
 ob=sources[key];bpy.context.collection.objects.link(ob)
 ob.name='SM_ThunderGodHammer_head_mount_'+key+'_V7'
 ob.hide_render=False;ob.hide_set(False);mesh=ob.data
 p=np.array([v.co[:] for v in mesh.vertices],dtype=np.float64)
 loop_ids=np.array([l.vertex_index for l in mesh.loops])
 normals=np.array([n.vector[:] for n in mesh.corner_normals],dtype=np.float64)
 final=deform(p,key)
 # Transport existing hard-edge normals through the local deformation.
 jac=np.empty((len(p),3,3),dtype=np.float64);eps=.00002
 for a in range(3):
  hi=p.copy();lo=p.copy();hi[:,a]+=eps;lo[:,a]-=eps
  jac[:,:,a]=(deform(hi,key)-deform(lo,key))/(2.*eps)
 transformed=np.linalg.solve(jac[loop_ids].transpose(0,2,1),normals[...,None])[...,0]
 transformed/=np.maximum(np.linalg.norm(transformed,axis=1,keepdims=True),1e-12)
 mesh.vertices.foreach_set('co',final.astype(np.float32).ravel());mesh.update()
 for face in mesh.polygons:face.use_smooth=True
 mesh.normals_split_custom_set(transformed.tolist())
 mesh.materials.append(inner);mesh.materials.append(buffer)
 if key=='laminated_damper':
  x,z,w=region(p);dark=(w>.70)&(seam_weight(z)>.88)
  for face in mesh.polygons:
   if np.mean(dark[list(face.vertices)])>.66:face.material_index=2
 if key=='ribbed_light':
  for side in (-1,1):
   cut=cutter(side)
   cut.data.materials.append(mesh.materials[0]);cut.data.materials.append(inner)
   for face in cut.data.polygons:face.material_index=1
   select(ob);mod=ob.modifiers.new('ActualThroughWindow_'+str(side),'BOOLEAN')
   mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
   bpy.ops.object.modifier_apply(modifier=mod.name)
   bpy.data.objects.remove(cut,do_unlink=True)
  mesh=ob.data;uv=mesh.uv_layers.active.data
  # New bore walls have their own planar UVs; original UVs remain untouched.
  for face in mesh.polygons:
   if face.material_index!=1:continue
   axis=int(np.argmax(np.abs(face.normal)))
   axes=[i for i in range(3) if i!=axis]
   for li in face.loop_indices:
    co=mesh.vertices[mesh.loops[li].vertex_index].co
    uv[li].uv=(co[axes[0]]/.025,co[axes[1]]/.025)
   face.use_smooth=False
 # Group names retain manufacturing intent in the editable source.
 protected=ob.vertex_groups.get('Original_Interface_Protected')
 if protected:ob.vertex_groups.remove(protected)
 protected=ob.vertex_groups.new(name='V7_NativeSealAndMatingFaces')
 coords=np.array([v.co[:] for v in mesh.vertices]);x=abs(coords[:,0]-CX)
 r=np.sqrt((x/.0535)**2+((coords[:,2]-CZ)/.0412)**2)
 ids=np.where((r<=1.045)|(x>=.0640)|(coords[:,2]<=.846))[0]
 protected.add(ids.tolist(),1.,'REPLACE')
 select(ob);mesh.calc_loop_triangles()
 bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
 slots={m.name:('/Game/Weapons/ThunderGodHammer20261028/SeatInlaidC6/'+m.name+'.'+m.name if m.name.startswith('M_ThorSeatC6_') else '/Game/Weapons/ThunderGodHammer20261028/CommonSeatsStructuralV7/'+m.name+'.'+m.name) for m in mesh.materials}
 counts={m.name:sum(f.material_index==i for f in mesh.polygons) for i,m in enumerate(mesh.materials)}
 rows.append(dict(id=key,mesh=ob.name,appearance=APPEARANCE[key],vertices=len(mesh.vertices),triangles=len(mesh.loop_triangles),bounds_m=[coords.min(axis=0).tolist(),coords.max(axis=0).tolist()],materials=slots,material_faces=counts,protected_vertices=len(ids),source_material='M_ThorSeatC6_'+key))
 ob.hide_render=True;ob.hide_set(True)
 print('STRUCTURAL_SEAT_EXPORTED',key,len(mesh.loop_triangles),flush=True)
 del p,final,jac,normals,transformed,loop_ids
sources['reinforced_block'].hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThorSeats_StructuralV7_Editable.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(complete=True,revision='CommonSeatsStructuralV7',parts=rows,concept='CommonSeats_Structural_Concept.png',source='SeatInlaidC6/ThorSeats_InlaidC6.blend',runtime_tested=False,rendered_model_preview=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('THREE_STRUCTURAL_SEATS_AUTHORED',flush=True)
