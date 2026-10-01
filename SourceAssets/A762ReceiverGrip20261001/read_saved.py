"""Read-only package reload following a commandlet Python shutdown exception."""
import hashlib,json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();r=json.loads((O/'install_receipt.json').read_text())
meta=json.loads((O/'Input/current.json').read_text());out={'assets':{},'game_tested':False,'purpose':'read saved packages after Python commandlet shutdown exception'}
for key,row in meta.items():
    path=row['path'].split('.')[0];file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=r['saved'][path]['sha256']:raise RuntimeError('Saved file changed '+path)
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Cannot load '+path)
    dm=u.DynamicMesh();fn=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh if key=='Body' else u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh
    result=fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
    if result[-1]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source load failed '+path)
    count=dm.get_triangle_count();uv=u.GeometryScript_MeshQueries.get_num_uv_sets(dm)
    if count!=r['saved'][path]['triangles'] or uv!=row['uv_sets']:raise RuntimeError('Saved source differs '+path)
    slots=mesh.materials if key=='Body' else mesh.static_materials
    if [s.material_interface.get_path_name() for s in slots]!=r['saved'][path]['materials']:raise RuntimeError('Saved material bindings differ '+path)
    out['assets'][key]={'loaded':True,'triangles':count,'uv_sets':uv,'saved_hash_matches':True}
    print('A762_SURFACE_DETAIL_RELOADED',key,count,flush=True)
(O/'saved_reload.json').write_text(json.dumps(out,indent=2));print('A762_SURFACE_DETAIL_RELOAD_COMPLETE',flush=True)
