"""Export native skin colour and material parameter names needed for the stablemaster."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out=root/'SourceAssets/HillsVillageStable/StablemasterR2/Inputs'
out.mkdir(parents=True,exist_ok=True)
native='/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face'
lib=u.MaterialEditingLibrary
records={}
for suffix in ['LOD1','LOD3','LOD5to7']:
    mat=u.load_asset(native+'/Materials/MI_Face_Skin_Baked_'+suffix)
    key='T_Head_'+suffix+'_BC'
    params=[str(n) for n in lib.get_texture_parameter_names(mat) if (v:=lib.get_material_instance_texture_parameter_value(mat,n)) and v.get_name()==key]
    if not params:raise RuntimeError('Missing native albedo parameter on '+mat.get_name())
    if suffix=='LOD1':
        src=u.load_asset(native+'/Baked/'+key)
        task=u.AssetExportTask();task.object=src;task.filename=str(out/'NativeBase.png')
        task.exporter=u.TextureExporterPNG();task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Base colour export failed')
    records[suffix]={'parent':mat.get_path_name(),'albedo':params}
(out/'skin.json').write_text(json.dumps(records,indent=2))
