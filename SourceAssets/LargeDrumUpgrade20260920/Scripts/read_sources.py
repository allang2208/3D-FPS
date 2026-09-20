"""Export current drum inputs, material bindings and package backups for authoring."""
import json
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LargeDrumUpgrade20260920')
paths={'M4':'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_LargeDrum',
       'AKM':'/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum',
       'QBZ191':'/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_drum'}
report={}
for gun,path in paths.items():
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError('Missing source '+path)
 t=u.AssetExportTask();t.object=mesh;t.filename=str(O/'Reference'/(gun+'_current.fbx'))
 t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX()
 t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.collision=False
 if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export failed '+gun)
 b=mesh.get_bounds()
 report[gun]={'asset':path,'fbx':t.filename,'bounds_origin_cm':[b.origin.x,b.origin.y,b.origin.z],
 'bounds_extent_cm':[b.box_extent.x,b.box_extent.y,b.box_extent.z],
 'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials],
 'import_source':mesh.get_editor_property('asset_import_data').get_first_filename()}
(O/'Reference/current_assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRUM_SOURCES_EXPORTED '+','.join(report))
