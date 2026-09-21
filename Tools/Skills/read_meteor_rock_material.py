import json
from pathlib import Path
import unreal as u
out=Path(u.Paths.project_dir()).resolve()/'SourceAssets/MeteorRealistic20260921'
lib=u.MaterialEditingLibrary
mat=u.load_asset('/Game/RuralAustralia/Presets/M_Nature_01')
instance=u.load_asset('/Game/RuralAustralia/StaticMeshes/Rocks/Rock_M_02/MI_Rock_M_02')
result={'properties':{},'scalars':{},'vectors':{},'switches':{},'expressions':[]}
for name in ['MP_BASE_COLOR','MP_ROUGHNESS','MP_NORMAL','MP_AMBIENT_OCCLUSION','MP_EMISSIVE_COLOR','MP_MATERIAL_ATTRIBUTES','MP_WORLD_POSITION_OFFSET']:
    prop=getattr(u.MaterialProperty,name)
    node=lib.get_material_property_input_node(mat,prop)
    result['properties'][name]=[str(node),lib.get_material_property_input_node_output_name(mat,prop)]
for name in lib.get_scalar_parameter_names(instance):result['scalars'][str(name)]=lib.get_material_instance_scalar_parameter_value(instance,name)
for name in lib.get_vector_parameter_names(instance):result['vectors'][str(name)]=str(lib.get_material_instance_vector_parameter_value(instance,name))
for name in lib.get_static_switch_parameter_names(instance):result['switches'][str(name)]=lib.get_material_instance_static_switch_parameter_value(instance,name)
for e in lib.get_material_expressions(mat):
    if 'Texture' in e.get_class().get_name():
        result['expressions'].append({'name':e.get_name(),'type':e.get_class().get_name(),'text':e.export_text() if hasattr(e,'export_text') else str(e)})
(out/'rock-material-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf8')
tex=u.load_asset('/Game/RuralAustralia/StaticMeshes/Rocks/Rock_M_02/T_Rock_M_02_CA')
task=u.AssetExportTask();task.object=tex;task.filename=str(out/'T_Rock_M_02_CA.png');task.automated=True;task.prompt=False;task.replace_identical=True
print('Texture export',u.Exporter.run_asset_export_task(task))
print(json.dumps(result,indent=2))
