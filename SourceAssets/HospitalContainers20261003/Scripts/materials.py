"""Save five restrained hospital coatings and an original label atlas material."""
import unreal as u


def create(root,base,report):
    assets=u.AssetToolsHelpers.get_asset_tools();edit=u.MaterialEditingLibrary;library=u.EditorAssetLibrary
    texture_path=base+'/Textures/T_Hospital_Labels';texture=u.load_asset(texture_path)
    if not texture:
        task=u.AssetImportTask();task.filename=str(root/'Authored/T_Hospital_Labels.png')
        task.destination_path=base+'/Textures';task.destination_name='T_Hospital_Labels';task.automated=True;task.save=False
        assets.import_asset_tasks([task]);texture=u.load_asset(texture_path)
        if not texture:raise RuntimeError('Hospital label import failed')
        texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        if not library.save_loaded_asset(texture,False):raise RuntimeError('Hospital label save failed')
    report['textures']=[texture_path]
    report['materials']=[]
    colors=[('White',(.58,.62,.58),.08,.49),('Blue',(.09,.20,.25),.0,.57),
            ('Green',(.105,.17,.14),.20,.47),('Red',(.38,.055,.045),.0,.48),('Lining',(.30,.34,.30),.0,.86)]
    for key,color,metallic,rough in colors:
        path=base+'/Materials/M_Hospital_'+key;material=u.load_asset(path)
        if not material:
            material=assets.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            material.set_editor_property('used_with_nanite',True)
            uv=edit.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-700,0)
            surface=edit.create_material_expression(material,u.MaterialExpressionCustom,-450,0)
            pin=u.CustomInput();pin.set_editor_property('input_name','UV');surface.set_editor_property('inputs',[pin])
            surface.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
            surface.set_editor_property('code','float2 q=floor(UV*120);float n=frac(sin(dot(q,float2(127.1,311.7)))*43758.5453);return .95+.05*n;')
            edit.connect_material_expressions(uv,'',surface,'UV')
            tint=edit.create_material_expression(material,u.MaterialExpressionConstant3Vector,-450,150)
            tint.set_editor_property('constant',u.LinearColor(*color,1))
            mix=edit.create_material_expression(material,u.MaterialExpressionMultiply,-200,50)
            edit.connect_material_expressions(surface,'',mix,'A');edit.connect_material_expressions(tint,'',mix,'B')
            edit.connect_material_property(mix,'',u.MaterialProperty.MP_BASE_COLOR)
            for value,property in ((metallic,u.MaterialProperty.MP_METALLIC),(rough,u.MaterialProperty.MP_ROUGHNESS)):
                node=edit.create_material_expression(material,u.MaterialExpressionConstant);node.set_editor_property('r',value)
                edit.connect_material_property(node,'',property)
            grain=edit.create_material_expression(material,u.MaterialExpressionCustom,-450,300)
            pin=u.CustomInput();pin.set_editor_property('input_name','UV');grain.set_editor_property('inputs',[pin])
            grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
            grain.set_editor_property('code','float fade=1-smoothstep(.025,.12,length(fwidth(UV))*500);return normalize(float3(sin(UV*1900)*.012*fade,1));')
            edit.connect_material_expressions(uv,'',grain,'UV');edit.connect_material_property(grain,'',u.MaterialProperty.MP_NORMAL)
            errors=list(edit.recompile_material(material))
            if errors:raise RuntimeError('Hospital coating compilation: '+str(errors))
            if not library.save_loaded_asset(material,False):raise RuntimeError('Hospital coating save failed')
        report['materials'].append(path)
    path=base+'/Materials/M_Hospital_Labels';material=u.load_asset(path)
    if not material:
        material=assets.create_asset('M_Hospital_Labels',base+'/Materials',u.Material,u.MaterialFactoryNew())
        material.set_editor_property('used_with_nanite',True)
        node=edit.create_material_expression(material,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',texture);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        edit.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        rough=edit.create_material_expression(material,u.MaterialExpressionConstant);rough.set_editor_property('r',.8)
        edit.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=list(edit.recompile_material(material))
        if errors:raise RuntimeError('Hospital label material compilation: '+str(errors))
        if not library.save_loaded_asset(material,False):raise RuntimeError('Hospital label material save failed')
    report['materials'].append(path)
