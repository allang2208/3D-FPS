"""Read the current host materials and export attachment references for authoring."""
import json
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/TacticalVerticalForegrip20260919/Integration')
R=O/'References';R.mkdir(parents=True,exist_ok=True)
paths={
 'M4':'/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
 'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'QBZ191':'/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
 'ASH12':'/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface'}
L=u.MaterialEditingLibrary
report={}
for gun,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 slots=[]
 for slot in mesh.materials:
  m=slot.material_interface
  slots.append({'slot':str(slot.material_slot_name),'material':m.get_path_name() if m else None})
 report[gun]={'mesh':path,'slots':slots}
old={'M4':'/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip',
     'AKM':'/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_vertical',
     'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_vertical',
     'ASH12':'/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_vertical'}
for gun,path in old.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 report[gun]['old_grip']=path
 report[gun]['old_slots']=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.static_materials]
 task=u.AssetExportTask();task.object=mesh;task.filename=str(R/(gun+'_vertical.fbx'))
 task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
 task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+gun)
(O/'host_sources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
