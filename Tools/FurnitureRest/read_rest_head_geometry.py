"""Export the neutral runtime head with weights mapped to copied body ancestors."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/BedNaturalV8')
source=json.loads((OUT/'authored.json').read_text());body_names=source['names']
asset=u.load_asset('/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head')
G,B,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_BoneWeights,u.GeometryScript_MeshQueries,u.GeometryScript_List
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
assert status==u.GeometryScriptOutcomePins.SUCCESS
_,bones=B.get_all_bones_info(dm)
mapped=[]
for i,b in enumerate(bones):
    while str(bones[i].name) not in body_names:
        i=bones[i].parent_index
        assert i>=0
    mapped.append(body_names.index(str(bones[i].name)))
_,p,_=Q.get_all_vertex_positions(dm,False);p=L.convert_vector_list_to_array(p)
_,t,_=Q.get_all_triangle_indices(dm,False);t=L.convert_triangle_list_to_array(t)
weights=[]
for i in range(len(p)):
    _,ws,valid=B.get_vertex_bone_weights(dm,i);assert valid
    row={}
    for w in ws:
        k=mapped[w.bone_index];row[k]=row.get(k,0)+w.weight
    weights.append([[b,w] for b,w in row.items() if w>0])
d={'source':asset.get_path_name(),'positions':[[v.x,v.y,v.z] for v in p],
   'triangles':[[v.x,v.y,v.z] for v in t],'bone_names':body_names,'weights':weights,
   'evaluation':'neutral face; CopyPoseFromMesh body ancestors; no facial animation'}
(OUT/'ReviewSaved/head.json').write_text(json.dumps(d,separators=(',',':')))
print('REST_HEAD_GEOMETRY_SAVED',len(p),len(t))
