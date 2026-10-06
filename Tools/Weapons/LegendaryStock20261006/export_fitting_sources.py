"""Read the installed stock interfaces and weapon reference frames for authoring."""
import json
import re
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[3]
O=P/'SourceAssets/LegendaryStock20261006/Integration'
(O/'Sources').mkdir(parents=True,exist_ok=True)
donors={
 'M4':'/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock',
 'AKM':'/Game/Weapons/TacticalTelescopicStock20260914/AKM/SM_TacticalTelescopicStock',
 'QBZ191':'/Game/Weapons/TacticalTelescopicStock20260914/QBZ191/SM_TacticalTelescopicStock',
 'M16':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic',
 'A762':'/Game/Weapons/A762/Accessories05/Meshes/SM_A762_tactical_telescopic',
 'SVD':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/Meshes/SM_SVD_tactical_telescopic',
 'PKM':'/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_tactical_telescopic',
 'LMG201':'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_tactical_telescopic',
 'HK416':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_tactical_telescopic'}
hosts={'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SK_QBZ191_Manny'}
for family,header in {'M16':'M16','A762':'A762','SVD':'SVD','PKM':'PKMLowpoly','LMG201':'LMG201','HK416':'HK416'}.items():
 hosts[family]=re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)"\)',(P/'Source/FPSGAME/Weapons'/(header+'WeaponAssets.h')).read_text(encoding='utf-8-sig'))[1]
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
report={}
for family,path in donors.items():
 mesh=u.load_asset(path);host=u.load_asset(hosts[family])
 if not mesh or not host:raise RuntimeError('Missing fitting source '+family)
 task=u.AssetExportTask();task.object=mesh;task.exporter=u.StaticMeshExporterFBX()
 task.filename=str(O/'Sources'/(family+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
 options=u.FbxExportOption();options.collision=False;options.level_of_detail=False;task.options=options
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+family)
 dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(host,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
 report[family]={'source':path,'fbx':task.filename,'host':host.get_path_name(),
  'bones':{str(b.name):pack(b.world_transform) for b in bones if str(b.name) in ('WPN_root','WPN_RearSight','WPN_FrontSight')},
  'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials]}
 (O/'fitting-sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('TACTICAL_STOCK_FITTING_SOURCE '+family,flush=True)
