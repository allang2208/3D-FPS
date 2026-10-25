import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/FurnitureRest20261022/RefineV2/Geometry'
OUT.mkdir(parents=True,exist_ok=True)
G,Q,B,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_BoneWeights,u.GeometryScript_List
def xyz(v):return [v.x,v.y,v.z]
def geometry(asset,skeletal=False):
 copier=G.copy_mesh_from_skeletal_mesh if skeletal else G.copy_mesh_from_static_mesh
 dm,status=copier(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Geometry copy '+asset.get_path_name())
 _,pv,_=Q.get_all_vertex_positions(dm,False);pv=L.convert_vector_list_to_array(pv)
 _,tv,_=Q.get_all_triangle_indices(dm,False);tv=L.convert_triangle_list_to_array(tv)
 data={'source':asset.get_path_name(),'positions':[xyz(v) for v in pv],'triangles':[xyz(t) for t in tv]}
 if skeletal:
  _,bones=B.get_all_bones_info(dm);data['bone_names']=[str(b.name) for b in bones]
  data['weights']=[]
  for i in range(len(pv)):
   _,ws,valid=B.get_vertex_bone_weights(dm,i)
   data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 return data

rows=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/furniture_rest.json').read_text(encoding='utf-8'))['furniture']
index={}
for i,row in enumerate(rows):
 path=OUT/(str(i)+'.json')
 if not path.exists():path.write_text(json.dumps(geometry(u.load_asset(row['mesh'])),separators=(',',':')))
 index[row['mesh']]=path.name
 print('GEOMETRY_EXPORTED',i,row['mesh'])
(OUT/'index.json').write_text(json.dumps(index,indent=2))
print('ALL_FURNITURE_GEOMETRY_EXPORTED',len(index))
