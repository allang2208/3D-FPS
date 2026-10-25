"""Capture the three actual apartment-bed meshes before adapting the new motion."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/FurnitureRest20261022/MeshyApartmentBed20261024/Geometry';OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((ROOT/'Content/ColdSteelData/apartment_furniture_rest.json').read_text(encoding='utf-8-sig'))
G,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
index={}
for profile in cfg['furniture']:
    if not any(s['kind']=='ApartmentBed' for s in profile['slots']):continue
    path=profile['mesh'];asset=u.load_asset(path)
    dm,status=G.copy_mesh_from_static_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    _,points,_=Q.get_all_vertex_positions(dm,False);points=L.convert_vector_list_to_array(points)
    _,triangles,_=Q.get_all_triangle_indices(dm,False);triangles=L.convert_triangle_list_to_array(triangles)
    name=str(len(index))+'.json';data={'source':path,'positions':[[p.x,p.y,p.z] for p in points],'triangles':[[p.x,p.y,p.z] for p in triangles]}
    (OUT/name).write_text(json.dumps(data,separators=(',',':')));index[path]=name
    print('APARTMENT_BED_GEOMETRY',path,len(points),flush=True)
(OUT/'index.json').write_text(json.dumps(index,indent=2))
