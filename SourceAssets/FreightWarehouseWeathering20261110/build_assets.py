"""Save the scoped weathering materials and obtain the existing paving surface."""
from pathlib import Path
import sys,json,gzip,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.modules.pop('materials',None)
import materials as M
receipt=ROOT/'Receipts/assets.json'
report=dict(stage='authoring',tests_run=False,rendered=False)
def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
record()
try:
    inputs=json.loads((ROOT/'inputs.json').read_text('utf8'))
    path=next(k for k in inputs['meshes'] if k.endswith('/SM_CargoWarehouse_Paving.SM_CargoWarehouse_Paving'))
    obj=u.load_asset(path);dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(obj,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    q=u.GeometryScript_MeshQueries;ls=u.GeometryScript_List
    pl=next(v for v in q.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
    tl=next(v for v in q.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
    geometry=dict(vertices=[list(v.to_tuple()) for v in ls.convert_vector_list_to_array(pl)],indices=[i for tri in ls.convert_triangle_list_to_array(tl) for i in (tri.x,tri.y,tri.z)])
    name='SM_CargoWarehouse_Paving.json.gz'
    with gzip.open(ROOT/'Geometry'/name,'wt',encoding='utf8') as f:json.dump(geometry,f,separators=(',',':'))
    inputs['meshes'][path]['geometry']=name
    (ROOT/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2),encoding='utf8')
    report.update(materials=M.build(),stage='assets_saved');record()
    print('FREIGHT_WEATHERING_ASSETS_SAVED',flush=True)
except Exception:
    report['error']=traceback.format_exc();record();raise
