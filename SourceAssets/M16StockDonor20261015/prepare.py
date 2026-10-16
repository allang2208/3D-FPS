"""Prepare the retained M16 receiver interface and identify potential donor packages."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];(O/'Input').mkdir(exist_ok=True)
paths={
 'M16':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic',
 'M4':'/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock',
 'HK416':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_tactical_telescopic',
 'SVD':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/Meshes/SM_SVD_tactical_telescopic'}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};R={'selected_donor':None,'assets':{}}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing '+path)
 disk=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
 mats,indices,names,status=u.GeometryScript_AssetUtils.get_section_material_list_from_static_mesh(mesh,u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 R['assets'][key]={'path':path,'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'dirty':path in dirty,'sections':[{'slot':i,'name':str(n),'material':m.get_path_name()} for m,i,n in zip(mats,indices,names)]}
 if key=='M16':
  if path in dirty:raise RuntimeError('M16 stock has unsaved changes; preserve it')
  backup=O/'Before/SM_M16_tactical_telescopic.uasset';backup.parent.mkdir(exist_ok=True)
  if not backup.exists():shutil.copy2(disk,backup)
  task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'Input/M16_Current.fbx');task.automated=True;task.prompt=False;task.replace_identical=False;task.options=u.FbxExportOption();task.options.level_of_detail=False
  if not u.Exporter.run_asset_export_task(task):raise RuntimeError('M16 source export failed')
  R['retained_interface_slot']='M16_InterfaceMetal'
(O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M16 receiver interface source retained; donor selection is pending. No production asset replaced.')
