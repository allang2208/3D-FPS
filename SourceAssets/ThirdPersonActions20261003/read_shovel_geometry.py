"""Read the shaft surface for third-person grip authoring; never saves the source asset."""
import json
from pathlib import Path
import unreal as u
r=Path(__file__).parent
a=u.load_asset('/Game/Shovel/SM_Ind_Mine_Tool_Shovel_Old_01')
lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
mesh,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),lod)
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(str(status))
raw=u.GeometryScript_MeshQueries.get_all_vertex_positions(mesh,False)
points=[]
for part in raw:
    if part.__class__.__name__=='GeometryScriptVectorList':
        for i in range(part.get_vector_list_length()):
            p=part.get_vector_list_item(i);p=p[0] if isinstance(p,tuple) else p
            points.append([p.x,p.y,p.z])
(r/'shovel-vertices.json').write_text(json.dumps(points))
print('SHOVEL_AUTHORING_VERTICES',len(points),flush=True)
