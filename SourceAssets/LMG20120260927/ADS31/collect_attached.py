import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;out={}
for name in ['FrontSight','RearSight','BipodBase','BipodLegA','BipodLegB']:
 mesh=u.load_asset('/Game/Weapons/LMG201/Production20260927/SM_LMG201_'+name)
 dm,res=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,v,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
 _,t,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
 out[name]={'vertices':[list(p.to_tuple()) for p in u.GeometryScript_List.convert_vector_list_to_array(v)],'triangles':[list(p.to_tuple()) for p in u.GeometryScript_List.convert_triangle_list_to_array(t)]}
(O/'attached.json').write_text(json.dumps(out,separators=(',',':')))
print('ADS31_STATIC_SOURCES',[(n,len(d['vertices'])) for n,d in out.items()],flush=True)
