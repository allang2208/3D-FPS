"""Read saved source-model positions for the scoped import comparison."""
import unreal as u,json,gzip
from pathlib import Path
O=Path(__file__).parent
G,Q,LU=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
def pick(result,t):return next(v for v in result if isinstance(v,t))
for key,path in [('before','/Game/Weapons/SVCH/Replacement20261018/SK_SVCH_Replacement'),('after','/Game/Weapons/SVCH/Replacement20261018/SightsR2/SK_SVCH_SightsR2')]:
 mesh=u.load_asset(path);dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
 result=G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
 if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Cannot read saved '+path)
 vs=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,False),u.GeometryScriptVectorList));ts=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,False),u.GeometryScriptTriangleList));ms=LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
 data={'path':path,'vertices':[[v.x,v.y,v.z] for v in vs],'triangles':[[t.x,t.y,t.z] for t in ts],'material_ids':list(ms),'materials':[str(s.material_slot_name) for s in mesh.materials]}
 with gzip.open(O/('saved_'+key+'.json.gz'),'wt') as f:json.dump(data,f,separators=(',',':'))
print('SIGHT_SAVED_GEOMETRY_READ',flush=True)
