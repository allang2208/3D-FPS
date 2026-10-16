"""Read the active stock packages for surface authoring; no gameplay execution."""
import unreal as u
import json, gzip, hashlib, shutil
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
I = O / 'Inputs'
I.mkdir(exist_ok=True)
paths = {
 'M4':'/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock',
 'AKM':'/Game/Weapons/TacticalTelescopicStock20260914/AKM/SM_TacticalTelescopicStock',
 'QBZ191':'/Game/Weapons/TacticalTelescopicStock20260914/QBZ191/SM_TacticalTelescopicStock',
 'M16':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic',
 'HK416':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_tactical_telescopic',
 'A762':'/Game/Weapons/A762/Accessories05/Meshes/SM_A762_tactical_telescopic',
 'PKM':'/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_tactical_telescopic',
 'SVD':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/Meshes/SM_SVD_tactical_telescopic',
 'LMG201':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_tactical_telescopic',
 'Super90':'/Game/Weapons/Super90/CommonStocks20261013/Meshes/SM_Super90_tactical_telescopic',
}
R = {'assets':{}, 'materials':{}, 'gameplay_tested':False}
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
L = u.MaterialEditingLibrary
for key, path in paths.items():
 obj = u.load_asset(path)
 if not obj: raise RuntimeError('Missing current stock '+path)
 disk = P/'Content'/(path.removeprefix('/Game/')+'.uasset')
 backup = O/'Before'/(path.removeprefix('/Game/')+'.uasset')
 backup.parent.mkdir(parents=True, exist_ok=True)
 if backup.exists(): raise RuntimeError('Preserve existing baseline '+str(backup))
 shutil.copy2(disk, backup)
 row = {'path':path, 'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
        'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in obj.static_materials]}
 dm,status = G.copy_mesh_from_static_mesh(obj,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Read failed '+path)
 _,pos,_ = Q.get_all_vertex_positions(dm,False)
 pos = u.GeometryScript_List.convert_vector_list_to_array(pos)
 _,tri,_ = Q.get_all_triangle_indices(dm,False)
 tri = u.GeometryScript_List.convert_triangle_list_to_array(tri)
 ids = [u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))]
 with gzip.open(I/(key+'.json.gz'),'wt',encoding='utf-8') as f:
  json.dump({'positions':[[v.x,v.y,v.z] for v in pos], 'triangles':[[t.x,t.y,t.z] for t in tri], 'materials':ids}, f)
 task=u.AssetExportTask();task.object=obj;task.filename=str(I/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=False
 task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task): raise RuntimeError(str(task.errors))
 row.update(vertices=len(pos),triangles=len(tri));R['assets'][key]=row
 for s in obj.static_materials:
  m=s.material_interface
  if not m or m.get_path_name() in R['materials']:continue
  mp=m.get_path_name();mr={'class':m.get_class().get_name()};R['materials'][mp]=mr
  if isinstance(m,u.MaterialInstanceConstant):
   mr['parent']=m.parent.get_path_name()
   mr['scalars']={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)}
   mr['textures']={str(n):(L.get_material_instance_texture_parameter_value(m,n).get_path_name() if L.get_material_instance_texture_parameter_value(m,n) else None) for n in L.get_texture_parameter_names(m)}
  else:
   mr['textures']={}
   for n in L.get_material_expressions(m):
    try:
     t=n.get_editor_property('texture')
     if t:mr['textures'][n.get_name()]=t.get_path_name()
    except Exception:pass
 (O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
 u.log('STOCK_SURFACE_INPUT '+key)
