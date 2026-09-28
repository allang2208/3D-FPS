"""Read/export only the current hub structure for the requested joint repair."""
import hashlib,json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
out=root/'FloorTrim';out.mkdir(exist_ok=True)
path='/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceStructure'
mesh=u.load_asset(path)
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved structure edits')
slots=[]
for s in mesh.get_editor_property('static_materials'):
    material=s.get_editor_property('material_interface')
    slots.append({'name':str(s.get_editor_property('material_slot_name')),'imported':str(s.get_editor_property('imported_material_slot_name')),
        'material':material.get_path_name() if material else None,'uv':s.get_editor_property('uv_channel_data').export_text()})
source=root.parents[2]/'Content/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceStructure.uasset'
task=u.AssetExportTask();task.object=mesh;task.filename=str(out/'SM_GodSpaceStructure_Before.fbx')
task.exporter=u.StaticMeshExporterFBX();task.automated=True;task.prompt=False;task.replace_identical=True
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Structure export failed')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'asset':path,'disk_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'slots':slots,
    'collision':str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
    'nanite':mesh.get_editor_property('nanite_settings').export_text(),
    'lod_count':mesh.get_num_lods(),'triangles':mesh.get_num_triangles(0),
    'editor_world':str(editor.get_editor_world()),'game_world':str(editor.get_game_world()),'export':task.filename}
(out/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('FLOOR_TRIM_INPUTS '+json.dumps(report))
