"""Map the bright pixels from the pre-edit camera to original static-mesh sections."""
from pathlib import Path
import gzip,json
import unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.get_actor_label()=='StationLine_AbandonedTransitStation_6')
    m=a.static_mesh_component.static_mesh
    mesh=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(m,mesh,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    q=u.GeometryScript_MeshQueries;ls=u.GeometryScript_List
    vl=next(v for v in q.get_all_vertex_positions(mesh,False) if isinstance(v,u.GeometryScriptVectorList))
    tl=next(v for v in q.get_all_triangle_indices(mesh,False) if isinstance(v,u.GeometryScriptTriangleList))
    getter=next(getattr(u.GeometryScript_Materials,n) for n in dir(u.GeometryScript_Materials) if n.startswith('get_all_triangle_material'))
    ml=next(v for v in getter(mesh) if isinstance(v,u.GeometryScriptIndexList))
    with gzip.open(R/'ceramic.json.gz','wt',encoding='utf8') as f:
        json.dump(dict(v=[v.to_tuple() for v in ls.convert_vector_list_to_array(vl)],t=[v.to_tuple() for v in ls.convert_triangle_list_to_array(tl)],slot=list(ls.convert_index_list_to_array(ml)),origin=a.get_actor_location().to_tuple()),f)
    return [m.get_path_name() for m in a.static_mesh_component.get_materials()]
