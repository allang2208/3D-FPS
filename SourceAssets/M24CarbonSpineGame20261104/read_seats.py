"""Read the two installed M24 receiver/stock assemblies and their live finishes."""
import unreal as u
from pathlib import Path
import hashlib,json
O=Path(__file__).resolve().parent
root='/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/'
rows={};dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for kind,meshname in [('Native','SM_M24_ReceiverStock_Native'),('Advanced','SM_M24_ReceiverStock_Advanced')]:
    path=root+meshname
    if path in dirty:raise RuntimeError('Unsaved assembly retained: '+path)
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing assembly: '+path)
    fn=O/'Inputs'/(kind+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(fn);task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    task.options.level_of_detail=False;task.options.collision=False;task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export '+path)
    file=Path(u.Paths.project_content_dir())/(path[6:]+'.uasset')
    rows[kind]={'asset':path,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'slots':[{'name':str(slot.material_slot_name),'material':slot.material_interface.get_path_name()} for slot in mesh.static_materials]}
(O/'Inputs'/'seats.json').write_text(json.dumps(rows,indent=2))
print('CARBON_SEATS_CAPTURED',list(rows))
