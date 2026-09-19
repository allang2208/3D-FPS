"""Export only the existing shared meshes needed for the ASH fitting author pass."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;(O/'Sources').mkdir(exist_ok=True)
paths={
 'vertical':'/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip',
 'canted':'/Game/Weapons/M4CantedForegrip/SM_CantedForegrip',
 'prism':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismHandstop',
 'angled':'/Game/Weapons/ResonanceGrip20260913/MeshyIntegration/M4/SM_ResonanceGrip'}
for key,name in [('holographic','SM_M4_Holographic'),('panoramic_red_dot','SM_PanoramicRedDot'),('prism_scope_2x','SM_PrismScope2X'),('lpvo_1_6x','SM_LPVO1to6X'),('lpvo_ring','SM_LPVORing')]:paths[key]='/Game/Weapons/ASH12/Surface20260919/Optics/'+name
result={}
for key,path in paths.items():
 obj=u.load_asset(path)
 if not obj:raise RuntimeError(path)
 task=u.AssetExportTask();task.object=obj;task.filename=str(O/'Sources'/(key+'.fbx'));task.automated=True;task.prompt=False
 task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+key)
 result[key]={'source':path,'fbx':task.filename,'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in obj.static_materials]}
(O/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ASH_ATTACHMENT_SOURCES_EXPORTED')
