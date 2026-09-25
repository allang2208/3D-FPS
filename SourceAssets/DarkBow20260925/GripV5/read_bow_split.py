import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
out={}
for key,path in [('original','/Game/Weapons/DarkBow20260925/SK_DarkBow'),('split','/Game/Weapons/DarkBow20260925/ArmsV2/SM_DarkBow_Riser')]:
    asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,pv,_=Q.get_all_vertex_positions(dm,False);_,tv,_=Q.get_all_triangle_indices(dm,False)
    vertices=u.GeometryScript_List.convert_vector_list_to_array(pv);triangles=u.GeometryScript_List.convert_triangle_list_to_array(tv)
    d={'positions':[[v.x,v.y,v.z] for v in vertices],'triangles':[[v.x,v.y,v.z] for v in triangles],
        'normals':[],'uv':[],'materials':[],'slots':[s.material_interface.get_path_name() for s in asset.static_materials]}
    for i in range(len(triangles)):
        _,a,b,c,valid=Q.get_triangle_normals(dm,i);d['normals'].append([[v.x,v.y,v.z] for v in (a,b,c)])
        a,b,c,valid=Q.get_triangle_u_vs(dm,0,i);d['uv'].append([[v.x,v.y] for v in (a,b,c)])
        d['materials'].append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0])
    out[key]=d
(P/'bow_split_source.json').write_text(json.dumps(out),encoding='utf-8')
print('BOW_SPLIT_SOURCE_READ',[(k,len(v['triangles'])) for k,v in out.items()])
