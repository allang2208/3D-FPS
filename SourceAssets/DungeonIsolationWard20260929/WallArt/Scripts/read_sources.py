"""Read and export imported poster meshes as placement authoring input; no scene edits."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Source';OUT.mkdir(parents=True,exist_ok=True)
records=[]
ar=u.AssetRegistryHelpers.get_asset_registry()
for item in sorted(ar.get_assets_by_path('/Game/HospitalCorridor/Meshes/Objects'),key=lambda a:str(a.asset_name)):
    if not str(item.asset_name).startswith('SM_HospitalPosters_'):continue
    mesh=item.get_asset();bounds=mesh.get_bounds()
    path=OUT/(str(item.asset_name)+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(path);task.automated=True;task.prompt=False
    task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    options=u.FbxExportOption();options.ascii=False;options.level_of_detail=False;options.collision=False
    task.options=options
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export source '+str(item.asset_name))
    records.append(dict(mesh=str(item.package_name),fbx=str(path),
        origin=[bounds.origin.x,bounds.origin.y,bounds.origin.z],extent=[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],
        materials=[s.material_interface.get_path_name() if s.material_interface else '' for s in mesh.get_editor_property('static_materials')]))
(ROOT/'sources.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('WARD_WALL_ART_SOURCES',len(records))
