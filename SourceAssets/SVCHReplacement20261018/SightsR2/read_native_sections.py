"""Read native follower section geometry without changing the V9 asset."""
import unreal as u
import json, gzip
from pathlib import Path
O=Path(__file__).parent
path='/Game/Characters/ModularOutfit20260924/BarePalmV7/SVD/SK_SVD_BareArmsV7'
mesh=u.load_asset(path);dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
def pick(r,t):return next(v for v in r if isinstance(v,t))
Q,L=u.GeometryScript_MeshQueries,u.GeometryScript_List
v=L.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,False),u.GeometryScriptVectorList))
t=L.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,False),u.GeometryScriptTriangleList))
m=L.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
data={'asset':path,'vertices':[[p.x,p.y,p.z] for p in v],'triangles':[[p.x,p.y,p.z] for p in t],'material_ids':list(m),'materials':[{'name':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
with gzip.open(O/'native_sections.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('SVCH_NATIVE_FOLLOWER_MATERIALS',json.dumps(data['materials']),flush=True)
