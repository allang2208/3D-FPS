"""Read the installed furnace material defaults needed to match the station."""
import json
from pathlib import Path
import unreal as u

root='/Game/Props/BlastFurnace20260923'
result={}
for name in ('Masonry','WroughtIron'):
    path=root+'/Materials/M_BlastFurnace_'+name
    material=u.load_asset(path)
    values={'path':path,'scalar':{},'vector':{},'textures':{}}
    for parameter in u.MaterialEditingLibrary.get_scalar_parameter_names(material):
        values['scalar'][str(parameter)]=u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(material,parameter)
    for parameter in u.MaterialEditingLibrary.get_vector_parameter_names(material):
        color=u.MaterialEditingLibrary.get_material_default_vector_parameter_value(material,parameter)
        values['vector'][str(parameter)]=[color.r,color.g,color.b,color.a]
    for parameter in u.MaterialEditingLibrary.get_texture_parameter_names(material):
        texture=u.MaterialEditingLibrary.get_material_default_texture_parameter_value(material,parameter)
        values['textures'][str(parameter)]=texture.get_path_name() if texture else None
    result[name]=values
out=Path(u.Paths.project_dir())/'SourceAssets/CastingStationRealism20260927/furnace-style-source.json'
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
