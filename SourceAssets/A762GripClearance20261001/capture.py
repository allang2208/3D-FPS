"""Read only the two current grip regions needed for the clearance edit."""
import array,hashlib,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;OUT=O/'Input';OUT.mkdir(parents=True,exist_ok=True)
P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
META={};Q,L,M=u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_Materials
def pick(r,c):return next(v for v in r if isinstance(v,c)) if isinstance(r,tuple) else r
for key,path,selected in [
 ('Body','/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',{'M_A762_FactoryRearGrip_Clean08'}),
 ('phantom_reargrip','/Game/Weapons/A762/Accessories05/Meshes/SM_A762_phantom_reargrip',{'A762_phantom_reargrip_0','A762_phantom_reargrip_Neck08'})]:
 mesh=u.load_asset(path);dm=u.DynamicMesh();body=key=='Body'
 slots=mesh.materials if body else mesh.static_materials;names=[str(s.material_slot_name) for s in slots]
 if not selected.issubset(names):raise RuntimeError('Current grip slots changed '+key)
 fn=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh if body else u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh
 fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
 if Q.get_has_vertex_id_gaps(dm) or Q.get_has_triangle_id_gaps(dm):raise RuntimeError('Sparse source IDs')
 vertices=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
 triangles=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
 materials=L.convert_index_list_to_array(pick(M.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
 indices=[i for i,s in enumerate(names) if s in selected];tids=[i for i,s in enumerate(materials) if s in indices]
 normals=array.array('f')
 for tid in tids:
  for n in [v for v in Q.get_triangle_normals(dm,tid) if isinstance(v,u.Vector)][:3]:normals.extend((n.x,n.y,n.z))
 header={'path':path,'vertices':len(vertices),'triangles':len(triangles),'selected_triangles':len(tids),
  'slots':names,'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots],
  'selected_slots':sorted(selected),'uv_sets':Q.get_num_uv_sets(dm)}
 with (OUT/(key+'.bin')).open('wb') as f:
  f.write((json.dumps(header)+'\n').encode())
  array.array('f',(c for v in vertices for c in (v.x,v.y,v.z))).tofile(f)
  array.array('i',tids).tofile(f)
  array.array('i',(c for tid in tids for c in (triangles[tid].x,triangles[tid].y,triangles[tid].z))).tofile(f)
  normals.tofile(f)
 file=P/'Content'/(path.removeprefix('/Game/')+'.uasset');META[key]={**header,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
 print('A762_SURFACE_CLEARANCE_INPUT',key,len(tids),flush=True)
(OUT/'current.json').write_text(json.dumps(META,indent=2))
