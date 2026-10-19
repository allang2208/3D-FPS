import unreal as u
import json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KCommon20261017')
R={};G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
for key,path in json.loads((O/'sources.json').read_text()).items():
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing source '+path)
 dm,status=G.copy_mesh_from_static_mesh(obj,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,vp,_=Q.get_all_vertex_positions(dm,False);verts=u.GeometryScript_List.convert_vector_list_to_array(vp)
 hi=max(v.z for v in verts);foot=[v for v in verts if v.z>hi-.25]
 R[key]={'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in obj.static_materials],
 'bounds':[[min(getattr(v,c) for v in verts) for c in 'xyz'],[max(getattr(v,c) for v in verts) for c in 'xyz']],
 'top_foot':[[min(getattr(v,c) for v in foot) for c in 'xyz'],[max(getattr(v,c) for v in foot) for c in 'xyz']],
 'sockets':{str(s.socket_name):[s.relative_location.x,s.relative_location.y,s.relative_location.z] for s in [obj.find_socket(n) for n in ('Emitter','AimGuide','Muzzle','Aim','ZoomRing','ZoomPivot')] if s}}
 (O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
 print('SAIGA_INPUT',key,flush=True)
