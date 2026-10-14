"""Read saved six assets and export their geometry for the requested mount check."""
import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent;X=O/'SavedExport';X.mkdir(exist_ok=True)
receipt=json.loads((O/'import-receipt.json').read_text())
if receipt.get('status')!='six_native_rail_variants_saved':raise RuntimeError('Import incomplete')
report={}
for key,e in receipt['saved'].items():
    mesh=u.load_asset(e['path']);error=0.
    if mesh is None:raise RuntimeError('Missing saved mesh '+key)
    for name,want in e['sockets'].items():
        socket=mesh.find_socket(name)
        if socket is None:raise RuntimeError('Missing socket '+key+' '+name)
        v=socket.relative_location;error=max(error,max(abs(a-b) for a,b in zip((v.x,v.y,v.z),want)))
    materials=[{'slot':str(s.material_slot_name),'path':s.material_interface.get_path_name() if s.material_interface else ''} for s in mesh.static_materials]
    if materials!=e['materials'] or error>.0001:raise RuntimeError('Saved bindings differ '+key)
    if any(s['slot']=='Tactical_Fitted_Bearing' for s in materials):raise RuntimeError('Rejected slot remains '+key)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(X/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
    report[key]={'path':mesh.get_path_name(),'socket_error_cm':error,'materials':materials,'section_count':mesh.get_num_sections(0),'fbx':task.filename}
    (O/'saved-readback.json').write_text(json.dumps(report,indent=2))
print('HK416_NATIVE_READBACK',len(report))
