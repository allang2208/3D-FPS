import unreal as u,json,array,hashlib
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();meta=json.loads((O/'Input/current.json').read_text())
for key,item in meta.items():
    path=item['path'].split('.')[0];file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Input changed '+key)
    mesh=u.load_asset(path);dm=u.DynamicMesh();G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
    fn=G.copy_mesh_from_skeletal_mesh if key=='Body' else G.copy_mesh_from_static_mesh
    fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
    with (O/'Input'/(key+'_extra_uv.bin')).open('wb') as f:
        for channel in range(1,item['uv_sets']):
            data=array.array('f')
            for tid in range(item['triangles']):
                for uv in Q.get_triangle_u_vs(dm,channel,tid)[:3]:data.extend((uv.x,uv.y))
            data.tofile(f)
    print('A762_SURFACE_DETAIL_UVS',key,item['uv_sets'],flush=True)
