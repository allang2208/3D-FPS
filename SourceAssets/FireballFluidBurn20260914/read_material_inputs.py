"""Read existing source material inputs needed for the combustion authoring."""
import json
from pathlib import Path
import unreal

lib = unreal.MaterialEditingLibrary
records = {}
for path in ['/Game/NiagaraExamples/Materials/MI_Distortion',
             '/Game/NiagaraExamples/Materials/MI_SmokeWispy_8x8_Emissive']:
    material = unreal.load_asset(path)
    records[path] = {
        'scalar': {str(key): lib.get_material_instance_scalar_parameter_value(material, key)
                   for key in lib.get_scalar_parameter_names(material)},
        'vector': {str(key): str(lib.get_material_instance_vector_parameter_value(material, key))
                   for key in lib.get_vector_parameter_names(material)},
        'texture': {str(key): str(lib.get_material_instance_texture_parameter_value(material, key))
                    for key in lib.get_texture_parameter_names(material)},
    }
output = Path(unreal.Paths.project_dir()) / 'SourceAssets/FireballFluidBurn20260914/material-inputs.json'
output.write_text(json.dumps(records, indent=2), encoding='utf-8')
unreal.log('FIREBALL_MATERIAL_INPUTS_READ')
