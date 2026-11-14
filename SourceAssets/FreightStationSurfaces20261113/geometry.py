from pathlib import Path
import unreal as u
import gzip,json
ROOT=Path(__file__).resolve().parent
def apply(w):
    registry=json.loads((ROOT/'done-01.json').read_text('utf8'))
    sections={'SM_Station_TunnelShell','SM_Station_TunnelSeals','SM_Station_RecoverySteps','SM_Station_Coping','SM_Station_Bridge','SM_Station_Stairs'}
    out=ROOT/'Geometry'
    out.mkdir(exist_ok=True)
    summary={}
    for row in registry:
        name=row['mesh'].split('.')[-1]
        if name not in sections or name in summary:continue
        mesh=u.load_asset(row['mesh'])
        dm=u.DynamicMesh()
        lod=u.GeometryScriptMeshReadLOD()
        lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        q=u.GeometryScript_MeshQueries
        ls=u.GeometryScript_List
        pl=next(v for v in q.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
        tl=next(v for v in q.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
        getter=next(getattr(u.GeometryScript_Materials,n) for n in dir(u.GeometryScript_Materials) if n.startswith('get_all_triangle_material'))
        ml=next(v for v in getter(dm) if isinstance(v,u.GeometryScriptIndexList))
        data=dict(vertices=[v.to_tuple() for v in ls.convert_vector_list_to_array(pl)],indices=[i for t in ls.convert_triangle_list_to_array(tl) for i in (t.x,t.y,t.z)],slots=list(ls.convert_index_list_to_array(ml)))
        with gzip.open(out/(name+'.json.gz'),'wt',encoding='utf8') as f:json.dump(data,f)
        summary[name]=len(data['slots'])
    return summary
