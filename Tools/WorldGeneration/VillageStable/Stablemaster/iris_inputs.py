from pathlib import Path
import json,unreal as u
r=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))/'SourceAssets/HillsVillageStable/StablemasterR2/Inputs'
lib=u.MaterialEditingLibrary
params={}
for side in 'LR':
    mat=u.load_asset('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/Materials/MI_Eye'+side+'_Baked')
    for n in lib.get_texture_parameter_names(mat):
        t=lib.get_material_instance_texture_parameter_value(mat,n)
        if t and t.get_name()=='T_EyeIris'+side+'_BC':
            task=u.AssetExportTask();task.object=t;task.filename=str(r/('Iris'+side+'.png'));task.exporter=u.TextureExporterPNG()
            task.automated=True;task.prompt=False;task.replace_identical=True
            if not u.Exporter.run_asset_export_task(task):raise RuntimeError('iris export')
            params[side]=dict(parent=mat.get_path_name(),parameter=str(n))
if len(params)!=2:raise RuntimeError('Both native iris parameters are needed')
(r/'iris.json').write_text(json.dumps(params,indent=2))
