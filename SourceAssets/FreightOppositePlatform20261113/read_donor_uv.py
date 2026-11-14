from pathlib import Path
import json,unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    m=next(a.static_mesh_component.static_mesh for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.get_actor_label()=='StationLine_AbandonedTransitStation_6')
    dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(m,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    q=u.GeometryScript_MeshQueries;fn=next(getattr(q,n) for n in dir(q) if n.replace('_','').lower()=='gettriangleuvs')
    data={i:[v.to_tuple() for v in fn(dm,0,int(i)) if isinstance(v,u.Vector2D)] for i in json.loads((R/'tile-plan.json').read_text('utf8'))['donors']}
    (R/'tile-uv.json').write_text(json.dumps(data),'utf8')
    return data
