"""Read only: candidate geometry/material inputs requested for meteor replacement."""
import json
from pathlib import Path
import unreal as u

OUT=Path(u.Paths.project_dir()).resolve()/'SourceAssets/MeteorRealistic20260921'
OUT.mkdir(parents=True,exist_ok=True)
sources=['/Game/NiagaraExamples/StaticMesh/S_Rock_shopk']
for name in ['Rock_S_01','Rock_S_02','Rock_M_01','Rock_M_02','Rock_M_03']:
    sources.append('/Game/RuralAustralia/StaticMeshes/Rocks/'+name+'/SM_'+name)
sources.append('/Game/MilitaryTrench/Assets/3D/Mil_Trench_Scatter_Rock_S_04/StaticMeshes/SM_Mil_Trench_Scatter_Rock_S_04')
rows=[]
for path in sources:
    mesh=u.load_asset(path)
    if not mesh:continue
    materials=[]
    for slot in mesh.get_editor_property('static_materials'):
        m=slot.get_editor_property('material_interface')
        row={'path':m.get_path_name(),'class':m.get_class().get_name()}
        if isinstance(m,u.MaterialInstanceConstant):
            row['parent']=m.get_editor_property('parent').get_path_name()
            for prop in ['texture_parameter_values','scalar_parameter_values','vector_parameter_values','static_parameters']:
                try:row[prop]=str(m.get_editor_property(prop))
                except Exception:pass
        materials.append(row)
    rows.append({'mesh':path,'bounds':str(mesh.get_bounds()),'triangles':mesh.get_num_triangles(0),'materials':materials})
(OUT/'candidate-inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
textures=[
    '/Game/NiagaraExamples/StaticMesh/Rock_shopk/T_Rock_shopk_2K_D',
    '/Game/RuralAustralia/StaticMeshes/Rocks/Rock_S_02/T_Rock_S_02_CA',
    '/Game/MilitaryTrench/Assets/3D/Mil_Trench_Scatter_Rock_S_04/Textures/T_Mil_Trench_Scatter_Rock_S_04_B',
]
for path in textures:
    tex=u.load_asset(path)
    # Let UE pick only an exporter whose SupportsObject accepts this source format.
    for ext in ['png','exr','tga']:
        task=u.AssetExportTask();task.object=tex;task.filename=str(OUT/(tex.get_name()+'.'+ext))
        task.automated=True;task.prompt=False;task.replace_identical=True
        if u.Exporter.run_asset_export_task(task):break
    else:raise RuntimeError('No supported texture exporter: '+path)
print(json.dumps(rows,indent=2))
