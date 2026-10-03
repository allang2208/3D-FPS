"""Preserve native split normals in the diagnostic renders."""
import json
from pathlib import Path
import unreal as u
HERE=Path(__file__).resolve().parent;IN=HERE/'Input'
for label in ['Bare','Brown','Black','Sleeve']:
    path=IN/(label+'.json');data=json.loads(path.read_text());asset=u.load_asset(data['asset'])
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(label)
    normals=[]
    for i in range(len(data['triangles'])):
        _,a,b,c,valid=u.GeometryScript_MeshQueries.get_triangle_normals(dm,i)
        if not valid:raise RuntimeError('Normal missing '+label)
        normals.append([[n.x,n.y,n.z] for n in [a,b,c]])
    data['normals']=normals;path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('PKM_NATIVE_NORMALS_READ')
