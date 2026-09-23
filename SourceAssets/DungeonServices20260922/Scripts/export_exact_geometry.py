"""Read source LOD0 for requested clearance inspection, avoiding Nanite fallback."""
import unreal as u
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for suffix,snapshot in [('', 'scene-before.json'),('_after','scene-after.json')]:
    scene=json.loads((ROOT/'Sources'/snapshot).read_text());out=[]
    for entry in scene['actors']:
        label=entry['label']
        if not any(k in label for k in ('Ceiling','Fixture','Vault','ConcreteSupports','ServicePipes','CableTray','HangingCables')):continue
        for c in entry['components']:
            mesh=u.load_asset(c['mesh']);dynamic=u.new_object(u.DynamicMesh)
            lod=u.GeometryScriptMeshReadLOD();lod.set_editor_property('lod_type',u.GeometryScriptLODType.SOURCE_MODEL);lod.set_editor_property('lod_index',0)
            dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh,dynamic,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
            if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read source LOD0 '+label)
            dm,vs,gaps=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
            vertices=u.GeometryScript_List.convert_vector_list_to_array(vs)
            dm,ts,gaps=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,True)
            triangles=u.GeometryScript_List.convert_triangle_list_to_array(ts)
            out.append(dict(actor=label,mesh=c['mesh'],v=[list(v.to_tuple()) for v in vertices],f=[list(t.to_tuple()) for t in triangles]))
    (ROOT/'Sources'/('geometry-source-lod0'+suffix+'.json')).write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    print('EXACT_GEOMETRY_READ',suffix or 'before',len(out))
