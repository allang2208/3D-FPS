"""Shared authoring of the grips' actual UE Substrate surfaces."""
import unreal as u
L=u.MaterialEditingLibrary
REVISION='SubstratePBR_20260927_V2'

def build_material(material,key,maps):
    # The project renders Substrate Front Material. Legacy channels alone leave
    # newly scripted materials without the authored surface in the active graph.
    L.delete_all_material_expressions(material)
    material.set_editor_property('use_material_attributes',False)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided',False)
    slab=L.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,320,0)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv=L.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-600,0)
    uv.set_editor_property('coordinate_index',0)
    inputs=[]
    for index,(suffix,prop,sampler,output,pin) in enumerate([
        ('BaseColor',u.MaterialProperty.MP_BASE_COLOR,u.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB','BaseColor'),
        ('Normal',u.MaterialProperty.MP_NORMAL,u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'RGB','Normal'),
        ('Roughness',u.MaterialProperty.MP_ROUGHNESS,u.MaterialSamplerType.SAMPLERTYPE_MASKS,'R','Roughness')]):
        sample=L.create_material_expression(material,u.MaterialExpressionTextureSample,-300,index*220)
        sample.set_editor_property('texture',maps[suffix]);sample.set_editor_property('sampler_type',sampler)
        if not L.connect_material_expressions(uv,'',sample,'UVs'):raise RuntimeError('UV0 connection failed')
        inputs.append((sample,output,prop,pin))
    for value,prop,pin in [(.9 if key=='Steel' else 0.,u.MaterialProperty.MP_METALLIC,'Metallic'),
                           (.5 if key=='Steel' else .35,u.MaterialProperty.MP_SPECULAR,'Specular')]:
        scalar=L.create_material_expression(material,u.MaterialExpressionConstant)
        scalar.set_editor_property('r',value);inputs.append((scalar,'',prop,pin))
    for source,output,prop,pin in inputs:
        if not L.connect_material_expressions(source,output,slab,pin):raise RuntimeError('Substrate input failed: '+pin)
        if not L.connect_material_property(source,output,prop):raise RuntimeError('Legacy mirror failed: '+pin)
    if not L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Substrate surface output connection failed')
    L.layout_material_expressions(material)
    errors=L.recompile_material(material)
    if errors:raise RuntimeError('Grip material compile failed: '+str(list(errors)))
    return {'material':material.get_path_name(),'revision':REVISION,'front_material':slab.get_path_name(),
            'texture_inputs':{k:v.get_path_name() for k,v in maps.items()},'compiler_errors':list(errors)}
