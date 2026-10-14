"""Read the current HK416 stock and donor for the requested small fit change."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;O.mkdir(exist_ok=True)
paths={'current':'/Game/Weapons/LegendaryStock20261006/Fitted/SM_TacticalStock_HK416',
       'donor':'/Game/Weapons/HK416/CommonAttachments20260930/Meshes/SM_HK416_tactical_telescopic'}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths.values()):raise RuntimeError('Preserve unsaved stock edits')
report={}
for key,path in paths.items():
    mesh=u.load_asset(path)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(O/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Source export failed '+key)
    report[key]={'asset':path,'fbx':task.filename,'materials':[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else ''} for s in mesh.static_materials]}
(O/'sources.json').write_text(json.dumps(report,indent=2))
print('HK416_STOCK_SOURCES_READY')
