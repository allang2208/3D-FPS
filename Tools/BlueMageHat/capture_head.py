import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageHat20261019';c=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
G,Q,L,B=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List,u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
for key,row in c['heads'].items():
    source=u.load_asset(row['mesh']);dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read saved head '+key)
    _,vs,_=Q.get_all_vertex_positions(dm,False);_,fs,_=Q.get_all_triangle_indices(dm,False);_,bones=B.get_all_bones_info(dm)
    data=dict(head=key,source=row['mesh'],positions=[xyz(v) for v in L.convert_vector_list_to_array(vs)],triangles=[xyz(f) for f in L.convert_triangle_list_to_array(fs)],bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
    (R/('native_head_'+key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8');print('HEAD_EQUIPMENT_NATIVE_REFERENCE',key,len(data['positions']),flush=True)
