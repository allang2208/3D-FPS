"""Author restrained industrial coatings with color, metallic, roughness and micro normals."""
import hashlib
import unreal as u


def create(root,base,report):
    assets=u.AssetToolsHelpers.get_asset_tools()
    edit=u.MaterialEditingLibrary
    library=u.EditorAssetLibrary
    source=root/'Authored/T_Treatment_Labels.png'
    texture_path=base+'/Textures/T_Treatment_Labels'
    texture=u.load_asset(texture_path)
    if not texture:
        task=u.AssetImportTask();task.filename=str(source)
        task.destination_path=base+'/Textures';task.destination_name='T_Treatment_Labels'
        task.automated=True;task.replace_existing=False;task.save=False
        assets.import_asset_tasks([task]);texture=u.load_asset(texture_path)
        if not texture:raise RuntimeError('Treatment label import failed')
        texture.set_editor_property('srgb',True)
        texture.set_editor_property('never_stream',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        if not library.save_loaded_asset(texture,False):raise RuntimeError('Treatment label save failed')
    report['textures']=[texture_path]
    report['label_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    report['materials']=[]
    coatings=[('Green',(.12,.21,.16),.12,.50),('Charcoal',(.065,.074,.076),.20,.55),
              ('Gray',(.28,.32,.30),.15,.47),('Ceramic',(.61,.57,.45),0,.35),
              ('Canvas',(.29,.26,.18),0,.86),('Paper',(.61,.59,.48),0,.84),
              ('Filter',(.51,.47,.37),0,.91)]
    for key,color,metallic,rough in coatings:
        path=base+'/Materials/M_Treatment_'+key
        material=u.load_asset(path)
        if not material:
            material=assets.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            material.set_editor_property('used_with_nanite',True)
            uv=edit.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-900,0)
            wear=edit.create_material_expression(material,u.MaterialExpressionVertexColor,-900,160)
            tint=edit.create_material_expression(material,u.MaterialExpressionConstant3Vector,-900,300)
            tint.set_editor_property('constant',u.LinearColor(*color,1))

            def custom(code,output,inputs,x,y):
                node=edit.create_material_expression(material,u.MaterialExpressionCustom,x,y)
                pins=[]
                for name,(origin,channel) in inputs.items():
                    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
                node.set_editor_property('inputs',pins)
                node.set_editor_property('output_type',output)
                node.set_editor_property('code',code)
                for name,(origin,channel) in inputs.items():edit.connect_material_expressions(origin,channel,node,name)
                return node

            paint=key in ('Green','Charcoal','Gray')
            common='float2 q=floor(UV*97);float n=frac(sin(dot(q,float2(127.1,311.7)))*43758.5453);'
            chip='float chip=smoothstep(.96,.995,n)*saturate(Wear*1.7+.035);'
            if paint:
                code=common+chip+'float soil=saturate(Soot*.6+.06*sin(UV.x*9+UV.y*11));return lerp(Tint*(.975+.025*n)*(1-soil*.25),float3(.22,.24,.22),chip);'
            else:
                code=common+'return Tint*(.955+.045*n);'
            inputs=dict(UV=(uv,''),Tint=(tint,''))
            if paint:inputs.update(Wear=(wear,'R'),Soot=(wear,'B'))
            surface=custom(code,u.CustomMaterialOutputType.CMOT_FLOAT3,inputs,-530,0)
            edit.connect_material_property(surface,'',u.MaterialProperty.MP_BASE_COLOR)
            if paint:
                metal=custom(common+chip+f'return lerp({metallic},.82,chip);',u.CustomMaterialOutputType.CMOT_FLOAT1,
                             dict(UV=(uv,''),Wear=(wear,'R')),-530,240)
            else:
                metal=edit.create_material_expression(material,u.MaterialExpressionConstant,-530,240)
                metal.set_editor_property('r',metallic)
            edit.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
            roughness=custom(common+f'return saturate({rough}+(n-.5)*.045);',u.CustomMaterialOutputType.CMOT_FLOAT1,
                             dict(UV=(uv,'')),-530,360)
            edit.connect_material_property(roughness,'',u.MaterialProperty.MP_ROUGHNESS)
            normal_code=('float fade=1-smoothstep(.025,.12,length(fwidth(UV))*500);'
                         'float2 grain=sin(UV*1900+sin(UV.yx*790));'
                         'return normalize(float3(grain*.014*fade,1));')
            if key=='Canvas':
                normal_code=('float fade=1-smoothstep(.02,.10,length(fwidth(UV))*480);'
                             'return normalize(float3(sin(UV.x*1700)*.034*fade,sin(UV.y*1700)*.026*fade,1));')
            normal=custom(normal_code,u.CustomMaterialOutputType.CMOT_FLOAT3,dict(UV=(uv,'')),-530,490)
            edit.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
            errors=list(edit.recompile_material(material))
            if errors:raise RuntimeError('Treatment material compilation '+key+': '+str(errors))
            if not library.save_loaded_asset(material,False):raise RuntimeError('Treatment coating save failed '+key)
        report['materials'].append(path)
    path=base+'/Materials/M_Treatment_Labels'
    material=u.load_asset(path)
    if not material:
        material=assets.create_asset('M_Treatment_Labels',base+'/Materials',u.Material,u.MaterialFactoryNew())
        material.set_editor_property('used_with_nanite',True)
        node=edit.create_material_expression(material,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',texture)
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        edit.connect_material_property(node,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        roughness=edit.create_material_expression(material,u.MaterialExpressionConstant)
        roughness.set_editor_property('r',.81)
        edit.connect_material_property(roughness,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=list(edit.recompile_material(material))
        if errors:raise RuntimeError('Treatment label compilation: '+str(errors))
        if not library.save_loaded_asset(material,False):raise RuntimeError('Treatment label material save failed')
    report['materials'].append(path)
