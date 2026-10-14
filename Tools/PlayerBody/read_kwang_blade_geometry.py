"""Read only the native weapon vertices to derive its blade frame, headless."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordKwang20261006')
mesh=u.load_asset('/Game/ParagonKwang/Characters/Heroes/Kwang/Meshes/Kwang_GDC')
dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
print('KWANG_GEOMETRY_COPY '+str(outcome))
_,infos=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
indices={b.index:str(b.name) for b in infos}
vertices=[]
_,vectors,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
positions=u.GeometryScript_List.convert_vector_list_to_array(vectors)
for i,v in enumerate(positions):
    _,weight,valid=u.GeometryScript_BoneWeights.get_largest_vertex_bone_weight(dm,i)
    name=indices.get(weight.bone_index,'')
    if valid and name=='weapon_r' and weight.weight>.9:
        vertices.append([v.x,v.y,v.z])
(OUT/'blade-geometry.json').write_text(json.dumps(dict(vertices=vertices,bones=indices)))
print('KWANG_BLADE_GEOMETRY_READY '+str(len(vertices)))
