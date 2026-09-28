"""Read the installed bench and export existing ammunition packages for placement."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
ROOT=P/'SourceAssets/GunWorkbenchAmmo20260928'
OUT=ROOT/'Sources';OUT.mkdir(parents=True,exist_ok=True)
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entry=next(e for e in palette.get_editor_property('components') if str(e.get_editor_property('id'))=='gun_workbench_table')
bench=entry.get_editor_property('mesh')
result={'bench':bench.get_path_name(),'bench_import_sources':list(bench.get_editor_property('asset_import_data').extract_filenames()),
        'game_running':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'ammo':{}}
for key in ('ammo_556','ammo_762'):
    path='/Game/Items/Consumables/'+key+'/SM_'+key
    mesh=u.load_asset(path)
    if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing existing ammo model: '+path)
    fbx=OUT/(key+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(fbx)
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False;task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed: '+path)
    result['ammo'][key]={'mesh':mesh.get_path_name(),'fbx':str(fbx),'bounds':str(mesh.get_bounds()),
        'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name()} for s in mesh.get_editor_property('static_materials')]}
(ROOT/'sources.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_AMMO_SOURCES '+json.dumps(result,ensure_ascii=False))
