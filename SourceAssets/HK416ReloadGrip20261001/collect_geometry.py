"""Read native bind-space mesh data without FBX's preview component exporter."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/HK416ReloadGrip20261001');P=O.parents[1];I=O/'Inputs'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=P.resolve():raise RuntimeError('Wrong project')
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
H='/Game/Weapons/HK416/Reworked20260930'
assets={'HK416':H+'/SK_HK416_Manny','factory':H+'/Attachments/SM_HK416_factory_magazine','extended':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_ext_mag','drum':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_large_drum'}
for name,path in assets.items():
 file=I/(name+'_geometry.json.gz')
 if file.exists():continue
 mesh=u.load_asset(path);copy=G.copy_mesh_from_skeletal_mesh if name=='HK416' else G.copy_mesh_from_static_mesh
 dm,status=copy(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read geometry '+path)
 _,ps,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(ps)
 _,ts,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(ts)
 data={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'pos':[[v.x,v.y,v.z] for v in ps],'tris':[[v.x,v.y,v.z] for v in ts],'bones':[],'weights':[]}
 if name=='HK416':
  _,bs=B.get_all_bones_info(dm);bs=sorted(bs,key=lambda b:b.index);data['bones']=[str(b.name) for b in bs]
  for i in range(len(ps)):
   _,ws,valid=B.get_vertex_bone_weights(dm,i);data['weights'].append([[w.bone_index,w.weight] for w in ws if w.weight>0])
 with gzip.open(file,'wt',encoding='utf8') as f:json.dump(data,f,separators=(',',':'))
 print('HK416_NATIVE_AUTHOR_GEOMETRY',name,len(ps),len(ts),flush=True)
