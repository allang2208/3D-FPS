"""Read texture semantics and current cloud reconstruction for production."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
report={'cvars':{},'textures':{},'noise_consumers':[]}
for name in ['r.VolumetricRenderTarget','r.VolumetricRenderTarget.Mode',
             'r.VolumetricCloud.ViewRaySampleMaxCount','r.VolumetricCloud.SampleMinCount',
             'r.VolumetricCloud.DistanceToSampleMaxCount','r.AntiAliasingMethod']:
    report['cvars'][name]=u.SystemLibrary.get_console_variable_float_value(name)
for name in ['T_CloudPattern','VT_PerlinWorley_Balanced']:
    tex=u.load_asset('/Engine/EngineSky/VolumetricClouds/'+name)
    props={}
    for p in ['srgb','compression_settings','mip_gen_settings','lod_bias','filter','source2d_texture','source2d_tile_size_x','source2d_tile_size_y']:
        try:props[p]=str(tex.get_editor_property(p))
        except Exception:pass
    report['textures'][name]=props
    source=u.load_asset('/Engine/EngineSky/VolumetricClouds/T_Volume_PerlinWorley_Balanced') if name.startswith('VT_') else None
    if source:
        task=u.AssetExportTask();task.object=source
        task.filename=str(root/'CloudSeaSources/ExistingCloudNoise.exr')
        task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export original volume atlas')
        report['textures'][name]['exported_source']=task.filename
mat=u.load_asset('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud')
expressions=list(u.MaterialEditingLibrary.get_material_expressions(mat))
for n in expressions:
    if isinstance(n,u.MaterialExpressionTextureSampleParameterVolume):
        row={'node':n.get_name(),'parameter':str(n.get_editor_property('parameter_name')),'consumers':[]}
        for target in expressions:
            inputs=u.MaterialEditingLibrary.get_inputs_for_material_expression(mat,target)
            if n in inputs:
                props={}
                for p in ['r','g','b','a','mask_r','mask_g','mask_b','mask_a','desc']:
                    try:props[p]=str(target.get_editor_property(p))
                    except Exception:pass
                row['consumers'].append({'class':target.get_class().get_name(),'node':target.get_name(),
                    'output':u.MaterialEditingLibrary.get_input_node_output_name_for_material_expression(target,n),**props})
        report['noise_consumers'].append(row)
(root/'Receipts/cumulus-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CUMULUS_AUTHORING_INPUTS '+json.dumps(report))
