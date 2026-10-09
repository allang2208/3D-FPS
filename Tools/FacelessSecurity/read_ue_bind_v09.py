"""Read/export the actual guard mesh for the reported shoulder defect."""
import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V09/Inputs');root.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/FacelessSecurity/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
report={'active_mesh':mesh.get_path_name(),'pie':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),
 'materials':[{'slot':str(m.material_slot_name),'material':m.material_interface.get_path_name() if m.material_interface else None} for m in mesh.get_editor_property('materials')]}
for asset,name in [(mesh,'UE_Active_V08'),(u.load_asset('/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Body_V06'),'UE_CompleteBody_V06')]:
    task=u.AssetExportTask();task.object=asset;task.filename=str(root/(name+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    options=u.FbxExportOption();options.set_editor_property('export_morph_targets',False);options.set_editor_property('level_of_detail',False);task.options=options
    report[name]={'exported':u.Exporter.run_asset_export_task(task),'errors':list(task.errors)}
(root/'active_mesh.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SECURITY_V09_SOURCE '+json.dumps(report))
