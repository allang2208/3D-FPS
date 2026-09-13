"""Read the active shared attachment inputs and export them for authoring."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D=O/'Sources';D.mkdir(exist_ok=True)
paths={
 'skeleton':'/Game/Weapons/ReferenceStock5080/SM_SkeletonStock',
 'qr_performance':'/Game/Weapons/QRPerformanceStock/M4/SM_QRPerformanceStock',
 'drum':'/Game/Weapons/M4Drum/SM_M4_LargeDrum',
 'suppressor':'/Game/Weapons/M4MuzzlesV1/SM_M4_suppressor',
 'brake':'/Game/Weapons/M4MuzzlesV1/SM_M4_brake',
 'titanium_brake':'/Game/Weapons/M4MuzzlesV1/SM_M4_titanium_brake',
 'holographic':'/Game/Weapons/M4Holographic/SM_M4_Holographic',
 'panoramic_red_dot':'/Game/Weapons/PanoramicRedDot/SM_PanoramicRedDot',
 'prism_scope_2x':'/Game/Weapons/PrismScope2XMachined/SM_PrismScope2X',
 'lpvo_1_6x':'/Game/Weapons/LPVO1to6X/SM_LPVO1to6X',
 'lpvo_ring':'/Game/Weapons/LPVO1to6X/SM_LPVORing',
 'vertical':'/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip',
 'canted':'/Game/Weapons/M4CantedForegrip/SM_CantedForegrip',
 'prism':'/Game/Weapons/PrismHandstopV1/SM_PrismHandstop',
 'angled':'/Game/Weapons/M4AngledForegripCompact75/SM_M4_AngledForegrip'}
report={}
for key,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Required attachment source missing: '+path)
 slots=[]
 for slot in mesh.static_materials:
  mat=slot.material_interface
  slots.append({'slot':str(slot.material_slot_name),'material':mat.get_path_name() if mat else None,'class':mat.get_class().get_name() if mat else None,'base':mat.get_base_material().get_path_name() if mat else None})
 task=u.AssetExportTask();task.object=mesh;task.filename=str(D/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
 option=u.FbxExportOption();option.ascii=False;option.level_of_detail=False;option.collision=False;task.options=option
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed: '+key)
 report[key]={'source':path,'fbx':task.filename,'slots':slots}
(O/'sources.json').write_text(json.dumps(report,indent=2))
methods=[x for x in dir(u.MaterialEditingLibrary) if any(k in x for k in ['input','expression','parameter'])]
(O/'material_api.json').write_text(json.dumps(methods,indent=2))
u.log('QBZ_ATTACHMENT_SOURCE_EXPORT_COMPLETE')
