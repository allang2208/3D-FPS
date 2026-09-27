import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'UEAfter';OUT.mkdir(exist_ok=True)
report={}
StaticEditor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for name in ('SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false','SM_Staff_grip_lining_alloy_grip','SM_Staff_grip_lining_pine_grip','SM_Staff_grip_lining_sandalwood_grip'):
    asset=u.load_asset('/Game/Weapons/ApprenticeStaff20260927/Meshes/'+name)
    task=u.AssetExportTask();task.object=asset;task.filename=str(OUT/(name+'_UE_After.fbx'));task.automated=True;task.prompt=False
    task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    task.options.set_editor_property('ascii',False)
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Mesh export failed '+name)
    b=asset.get_bounds();report[name]={'size_cm':[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2],
        'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in asset.static_materials],
        'export':task.filename,'full_precision_uvs':StaticEditor.get_lod_build_settings(asset,0).use_full_precision_u_vs}
(ROOT/'ue_after.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STAFF_V19_ACTIVE_ASSETS_EXPORTED')
