"""Refine and engrave the original GuanLei-compatible solid; preserve original UVs and interfaces."""
import bpy,bmesh,numpy as np,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from design import STYLES,fields,deformation,CX,CZ
for f in ['Export','Textures','Data']:(P/f).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_factory']
factory=b.objects[0];bpy.context.collection.objects.link(factory);src=factory.data
bm=bmesh.new();bm.from_mesh(src);normal_layer=bm.loops.layers.float_vector.new('NativeNormal')
for f,poly in zip(bm.faces,src.polygons):
 for loop,li in zip(f.loops,poly.loop_indices):loop[normal_layer]=src.corner_normals[li].vector
def patch(v):
 x=abs(v.co.x-CX);z=v.co.z
 return .026<x<.0635 and .848<z<.977 and abs(v.co.y)>.018 and (x/.0535)**2+((z-CZ)/.0412)**2>1.045**2
# Density is restricted to carved shoulder regions; the seal and interfaces keep
# their factory tessellation. Existing per-corner normals/UVs interpolate locally.
for step in range(4):
 edges=[e for e in bm.edges if e.calc_length()>.00065 and all(patch(v) for v in e.verts)]
 if not edges:break
 bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
 print('LOCAL_REFINEMENT',step,len(edges),flush=True)
bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3],quad_method='BEAUTY',ngon_method='BEAUTY')
normals=np.array([tuple(l[normal_layer]) for f in bm.faces for l in f.loops],np.float64)
template=bpy.data.meshes.new('Factory_CarvingTemplate');bm.to_mesh(template);bm.free()
for f in template.polygons:f.use_smooth=True
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
template.normals_split_custom_set(normals.tolist())
positions=np.array([tuple(v.co) for v in template.vertices],np.float64)
loop_vertices=np.array([l.vertex_index for l in template.loops],np.int32)
original_loop_positions=positions[loop_vertices]
rows=[]
for s in STYLES:
 mesh=template.copy();obj=bpy.data.objects.new('SM_ThunderGodHammer_head_mount_'+s['id'],mesh);bpy.context.collection.objects.link(obj)
 p=positions.copy();p[:,1]+=deformation(positions,s)
 mesh.vertices.foreach_set('co',p.astype(np.float32).ravel())
 # Inverse-transpose Jacobian of local Y displacement preserves native hard
 # normals elsewhere and gives the real groove walls their own surface normals.
 eps=.000025;derivatives=[]
 for axis in range(3):
  plus=positions.copy();minus=positions.copy();plus[:,axis]+=eps;minus[:,axis]-=eps
  derivatives.append((deformation(plus,s)-deformation(minus,s))/(2*eps))
 dx,dy,dz=[v[loop_vertices] for v in derivatives];nn=normals.copy();ny=normals[:,1]/np.maximum(1+dy,.1)
 nn[:,0]-=ny*dx;nn[:,1]=ny;nn[:,2]-=ny*dz;nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
 mesh.update();mesh.normals_split_custom_set(nn.tolist());mesh.calc_loop_triangles();mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
 uv=np.array([tuple(l.uv) for l in mesh.uv_layers[0].data],np.float32)
 tangents=np.array([tuple(l.tangent) for l in mesh.loops],np.float32);bits=np.array([tuple(l.bitangent) for l in mesh.loops],np.float32)
 triangles=np.array([tuple(t.loops) for t in mesh.loop_triangles],np.int32)
 np.savez_compressed(P/'Data'/(s['id']+'.npz'),position=original_loop_positions.astype(np.float32),uv=uv,tangent=tangents,bitangent=bits,triangles=triangles)
 mat=bpy.data.materials.new('M_GuanLeiC8_'+s['id']);mesh.materials.clear();mesh.materials.append(mat)
 for f in mesh.polygons:f.material_index=0
 group=obj.vertex_groups.new(name='Original_Interface_Protected')
 protected=np.where(np.abs(deformation(positions,s))<1e-10)[0];group.add(protected.tolist(),1,'REPLACE')
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
 rows.append(dict(id=s['id'],name=s['name'],mesh=obj.name,material=mat.name,appearance=s['appearance'],triangles=len(mesh.loop_triangles),vertices=len(mesh.vertices),modified_vertices=int(np.sum(np.abs(p[:,1]-positions[:,1])>1e-9)),protected_vertices=len(protected),bounds_m=[p.min(axis=0).tolist(),p.max(axis=0).tolist()],textures={k:'Textures/T_GuanLeiC8_'+s['id']+'_'+k+'.png' for k in ['BaseColor','ORM','Normal']}))
 obj.hide_render=True;obj.hide_set(True);print('CARVED',s['id'],len(mesh.loop_triangles),flush=True)
factory.hide_render=True;factory.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLei_ReturnC8_Editable.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(complete=True,parts=rows,concept=str(P.parent/'SeatNorseConceptV5/C_InlaidThunder.png'),method='Original solid locally subdivided and directly carved; continuous embedded silver floors; no extra strap meshes',uv='Original UV0 retained and locally interpolated',normal_convention='OpenGL; UE flip_green_channel=True; UE recomputes tangents',texture_resolution=4096,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_C8_GEOMETRY_EXPORTED',flush=True)
