import gzip,json
from pathlib import Path
import unreal as u
def run(w,row):
    a=u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor)
    data={}
    for obj in a:
        c=obj.static_mesh_component
        if not c.static_mesh:continue
        n=c.static_mesh.get_name()
        if not any(s in n.lower() for s in ('walls','wallpanels','wallclad','column','partition','platformwall','infill','backwall','workshopwall','backing','station_arch','station_shell')):continue
        p,e=obj.get_actor_bounds(False)
        if all(abs(p.x-x)>e.x+620 or abs(p.y-y)>e.y+630 for x,y in [(2952,341),(8428,-310)]):continue
        mesh=c.static_mesh;dm=u.DynamicMesh(); lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        positions=next(v for v in u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
        faces=next(v for v in u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
        xs=c.get_world_transform()
        data[obj.get_actor_label()]=dict(v=[xs.transform_location(p).to_tuple() for p in u.GeometryScript_List.convert_vector_list_to_array(positions)],f=[[t.x,t.y,t.z] for t in u.GeometryScript_List.convert_triangle_list_to_array(faces)])
    with gzip.open(Path(__file__).with_name('visible-walls.json.gz'),'wt',encoding='utf-8') as f:json.dump(data,f)
