"""Read the saved UE meshes, check emitter/material preservation, export geometry."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;X=O/'SavedExport';X.mkdir(exist_ok=True)
receipt=json.loads((O/'import-receipt.json').read_text())
report={}
for key,e in receipt['saved'].items():
    mesh=u.load_asset(e['path'])
    if mesh is None:raise RuntimeError('Saved mesh not found '+key)
    error=0.
    for name,want in e['sockets'].items():
        sock=mesh.find_socket(name)
        if sock is None:raise RuntimeError('Missing socket '+key+' '+name)
        p=sock.relative_location;error=max(error,max(abs(a-b) for a,b in zip((p.x,p.y,p.z),want)))
    actual=[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else ''} for s in mesh.static_materials]
    if actual!=e['materials'] or error>.0001:raise RuntimeError('Saved bindings mismatch '+key)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(X/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Saved mesh export failed '+key)
    report[key]={'path':mesh.get_path_name(),'socket_error_cm':error,'materials_match':True,'fbx':task.filename}
    (O/'saved-readback.json').write_text(json.dumps(report,indent=2))
print('FITTED_TACTICAL_READBACK '+str(len(report)))
