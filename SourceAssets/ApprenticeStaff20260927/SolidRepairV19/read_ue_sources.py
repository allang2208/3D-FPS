import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Inputs';OUT.mkdir(exist_ok=True)
report={}
for stem in ('T_WoodSurface_00A','T_LS_BlackAlderBark_00A'):
    for suffix in ('BaseColor','Normal','RHAOM'):
        name=stem+'_'+suffix;asset=u.load_asset('/Game/UnrealNormandy/Textures/'+name)
        if not asset:raise RuntimeError('Missing source texture '+name)
        task=u.AssetExportTask();task.object=asset;task.filename=str(OUT/(name+'.png'));task.automated=True;task.prompt=False
        task.replace_identical=True;task.exporter=u.TextureExporterPNG()
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+name)
        report[name]={'source':asset.get_path_name(),'export':task.filename,'srgb':asset.get_editor_property('srgb')}
for name in ('SM_Staff_Body','SM_Staff_head_crystal_false','SM_Staff_grip_lining_false'):
    asset=u.load_asset('/Game/Weapons/ApprenticeStaff20260927/Meshes/'+name)
    task=u.AssetExportTask();task.object=asset;task.filename=str(OUT/(name+'_UE_Before.fbx'));task.automated=True;task.prompt=False
    task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    task.options.set_editor_property('ascii',False)
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Mesh export failed '+name)
    b=asset.get_bounds();report[name]={'size_cm':[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2],
        'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in asset.static_materials]}
(ROOT/'ue_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('STAFF_V19_SOURCES_EXPORTED')
