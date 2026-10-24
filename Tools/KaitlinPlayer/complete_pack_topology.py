"""Read harness topology for retaining volume during jacket fitting."""
import json
from pathlib import Path
import unreal as u
def main():
    P=Path('D:/FPS3D/FPSGAME');W=P/'SourceAssets/KaitlinCompletion20261024/Packs'
    read=lambda p:json.loads(p.read_text('utf-8-sig'))
    index=read(W/'inputs.json')
    for path,row in index.items():
        if row['kind']!='pack':continue
        file=W/row['file'];data=read(file)
        if 'triangles' in data:continue
        mesh,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(u.load_asset(path),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read pack topology')
        _,faces,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(mesh,False)
        data['triangles']=[[t.x,t.y,t.z] for t in u.GeometryScript_List.convert_triangle_list_to_array(faces)]
        file.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    (P/'SourceAssets/KaitlinPlayer20261023/complete_pack_topology_status.json').write_text(json.dumps({'remaining':0,'complete':True}))
main()
