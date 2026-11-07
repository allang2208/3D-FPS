from pathlib import Path
import json,collections,unreal as u
O=Path(__file__).resolve().parent
rec=json.loads((O/'saved.json').read_text())
result={};Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;L=u.GeometryScript_List
for k,row in rec['meshes'].items():
    mesh=u.load_asset(row['path']);lods=[]
    for li in range(mesh.get_num_lods()):
        dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.RENDER_DATA,lod_index=li))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('render geometry read '+k)
        _,ms,valid=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
        counts=collections.Counter(L.convert_index_list_to_array(ms))
        lods.append({str(mesh.static_materials[i].material_slot_name):n for i,n in counts.items()})
    result[k]=lods
(O/'active-sections.json').write_text(json.dumps(result,indent=2))
print('M24_JUNCTION_RENDER_SECTIONS',result)
