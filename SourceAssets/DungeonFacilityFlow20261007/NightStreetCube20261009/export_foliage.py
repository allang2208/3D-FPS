"""Export already-owned foliage material images for the offline street bake."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Sources/Foliage';OUT.mkdir(parents=True,exist_ok=True)
report=[];exported=set()
for name in ('Tree_M_01','Tree_M_03'):
    mesh=u.load_asset('/Game/RuralAustralia/StaticMeshes/Vegetation/'+name+'/SM_'+name)
    if not mesh:raise RuntimeError('Existing ecology source missing: '+name)
    item=dict(name=name,source=mesh.get_path_name(),slots=[])
    for slot in mesh.get_editor_property('static_materials'):
        mat=slot.material_interface;row=dict(slot=str(slot.material_slot_name),material=mat.get_path_name(),textures=[])
        for parameter in u.MaterialEditingLibrary.get_texture_parameter_names(mat):
            tex=u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,parameter)
            if not tex or not isinstance(tex,u.Texture2D):continue
            path=OUT/(tex.get_name()+'.png')
            if tex.get_path_name() not in exported:
                task=u.AssetExportTask();task.object=tex;task.exporter=u.TextureExporterPNG();task.filename=str(path)
                task.automated=True;task.prompt=False;task.replace_identical=True
                if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Could not export '+tex.get_path_name())
                exported.add(tex.get_path_name())
            row['textures'].append(dict(parameter=str(parameter),source=tex.get_path_name(),file=str(path),srgb=tex.get_editor_property('srgb')))
        item['slots'].append(row)
    report.append(item)
(OUT/'materials.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('OFFLINE_FOLIAGE_SOURCES_EXPORTED',len(exported))
