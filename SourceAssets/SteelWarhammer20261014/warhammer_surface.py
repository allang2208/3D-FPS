"""Warhammer PBR surface for the project's active Substrate renderer."""
import unreal as u

def build_surface(material, textures):
    lib=u.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    material.set_editor_property('use_material_attributes',False)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('used_with_skeletal_mesh',True)
    surface=lib.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels,300,0)
    surface.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv=lib.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-650,0)
    uv.set_editor_property('coordinate_index',0)
    samples={}
    for i,key in enumerate(('BaseColor','MetallicRoughness','Normal')):
        if not textures.get(key):raise RuntimeError('Missing warhammer texture '+key)
        node=lib.create_material_expression(material,u.MaterialExpressionTextureSample,-350,i*220)
        node.set_editor_property('texture',textures[key])
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if key=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        if not lib.connect_material_expressions(uv,'',node,'UVs'):raise RuntimeError('UV0 connection failed')
        samples[key]=node
    for key,channel,pin,prop in (
        ('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),
        ('MetallicRoughness','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),
        ('MetallicRoughness','B','Metallic',u.MaterialProperty.MP_METALLIC),
        ('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL)):
        if not lib.connect_material_expressions(samples[key],channel,surface,pin):raise RuntimeError('Substrate input failed: '+pin)
        if not lib.connect_material_property(samples[key],channel,prop):raise RuntimeError('Legacy input failed: '+pin)
    if not lib.connect_material_property(surface,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate surface output failed')
    lib.layout_material_expressions(material)
    errors=list(lib.recompile_material(material))
    if errors:raise RuntimeError('Warhammer material compilation failed: '+str(errors))
    return {'material':material.get_path_name(),'front_material':surface.get_path_name(),
        'textures':{key:tex.get_path_name() for key,tex in textures.items()},'compiler_errors':errors}
