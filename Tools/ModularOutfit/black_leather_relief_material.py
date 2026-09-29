"""Save the glove-scale counterpart of the dungeon/carpet shared-POM method."""
import unreal as u


def build(group,root,destination,save,load,shader_path):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
    folder=destination+'/Materials/'+group;E.make_directory(folder)
    textures={}
    for channel in ('BaseColor','ORM','Normal','Relief'):
        name='T_BlackLeather_'+group+'_'+channel
        task=u.AssetImportTask();task.filename=str(root/'Textures'/group/(name+'.png'))
        task.destination_path=folder;task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);tex=load(folder+'/'+name)
        tex.set_editor_property('srgb',channel=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal'
            else u.TextureCompressionSettings.TC_MASKS if channel in ('ORM','Relief') else u.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property('never_stream',False)
        tex.set_editor_property('max_texture_size',4096 if group=='M4' else 2048)
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
        if channel=='Normal':tex.set_editor_property('flip_green_channel',True)
        save(tex);textures[channel]=tex
    name='M_BlackLeatherReliefCuff_'+group
    mat=u.load_asset(folder+'/'+name) or A.create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    if not L.get_material_expressions(mat):
        mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)
        mat.set_editor_property('tangent_space_normal',True)
        mat.set_editor_property('use_material_attributes',True)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_STATIC_MESH)
        def node(cls):return L.create_material_expression(mat,cls)
        def wire(a,b,pin,output=''):
            if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
        def scalar(name,value):
            n=node(u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name)
            n.set_editor_property('default_value',value);return n
        def texture(channel):
            n=node(u.MaterialExpressionTextureObjectParameter);n.set_editor_property('parameter_name',channel)
            n.set_editor_property('texture',textures[channel]);n.set_editor_property('sampler_type',
                u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else
                u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            return n
        uv=node(u.MaterialExpressionTextureCoordinate)
        pos=node(u.MaterialExpressionWorldPosition)
        pos.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        inputs={'UV':uv,'Position':pos,'Camera':node(u.MaterialExpressionCameraPositionWS),
            'VertexNormal':node(u.MaterialExpressionVertexNormalWS),
            'DepthCm':scalar('LeatherReliefDepthCm',.08),
            'TextureSize':scalar('AtlasResolution',4096 if group=='M4' else 2048),
            'FuzzAmount':scalar('ShortFiberFuzz',.30),
            'ColorTex':texture('BaseColor'),'NormalTex':texture('Normal'),
            'ORMTex':texture('ORM'),'ReliefTex':texture('Relief')}
        shader=node(u.MaterialExpressionCustom);shader.set_editor_property('code',shader_path.read_text(encoding='utf8'))
        shader.set_editor_property('description','Skinned atlas shared shallow POM, seam fade and short leather/textile nap')
        shader.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT4)
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        shader.set_editor_property('inputs',pins)
        for name,source in inputs.items():wire(source,shader,name)
        outputs=[]
        for name,width in [('NormalTangent',3),('AO',1),('Fuzz',1)]:
            output=u.CustomOutput();output.set_editor_property('output_name',name)
            output.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
            outputs.append(output)
        shader.set_editor_property('additional_outputs',outputs)
        attrs=node(u.MaterialExpressionMakeMaterialAttributes)
        if not L.connect_material_property(attrs,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Cannot bind material attributes')
        for channels,pin in [('rgb','BaseColor'),('a','Roughness')]:
            mask=node(u.MaterialExpressionComponentMask)
            for key in 'rgba':mask.set_editor_property(key,key in channels)
            wire(shader,mask,'');wire(mask,attrs,pin)
        wire(shader,attrs,'Normal','NormalTangent');wire(shader,attrs,'AmbientOcclusion','AO')
        # Cloth maps CustomData0 / the attributes ClearCoat input to fuzz.
        wire(shader,attrs,'ClearCoat','Fuzz');wire(scalar('LeatherSpecular',.30),attrs,'Specular')
        wire(scalar('LeatherMetallic',0.),attrs,'Metallic')
        fuzz=node(u.MaterialExpressionVectorParameter);fuzz.set_editor_property('parameter_name','FiberFuzzColor')
        fuzz.set_editor_property('default_value',u.LinearColor(.065,.071,.079,1))
        wire(fuzz,attrs,'SubsurfaceColor')
        L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Glove relief shader compilation failed: '+str(errors))
    save(mat);return mat
