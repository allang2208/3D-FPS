"""Create the opaque materials paired with the relief kit's UVs and displacement."""
def relief_materials():
    dest=DEST+'/Textures/Surfaces'
    source=ROOT/'Surfaces'/'Prepared'
    result={}
    # The mesh already carries centimetre-scale relief. Only the residual recess uses bump offset.
    for slot,ratio,tint in [('Wall',.0065,(.87,.84,.79)),
                            ('Flagstone',.0025,(.88,.84,.81)),('Timber',.0018,(.81,.80,.77))]:
        path=DEST+'/Materials/M_Chapel'+slot
        if os.environ.get('CHAPEL_RESUME')=='1' and E.does_asset_exist(path) and slot not in os.environ.get('CHAPEL_SURFACES','').split():
            result[slot]=get(path)
            continue
        mat=create_mat('M_Chapel'+slot)
        def node(kind):return L.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
        def link(src,pin,dst,name):
            if not L.connect_material_expressions(src,pin,dst,name):
                raise RuntimeError(f'{slot} cannot wire {name} on {dst.get_name()}. Inputs {L.get_material_expression_input_names(dst)}')
        def constant(value):
            n=node('Constant');n.r=value;return n
        def param(name,value):
            n=node('ScalarParameter')
            n.set_editor_property('parameter_name',name)
            n.set_editor_property('default_value',value)
            return n
        def times(a,b):
            n=node('Multiply');link(a,'',n,'A');link(b,'',n,'B');return n
        def smooth(a,b,x):
            n=node('SmoothStep');link(constant(a),'',n,'Min');link(constant(b),'',n,'Max');link(x,'',n,'Value');return n
        def sample(tex,uv):
            n=node('TextureSample');n.texture=tex
            n.sampler_type=({'NormalDX':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ARH':u.MaterialSamplerType.SAMPLERTYPE_MASKS}.get(tex.get_name().split('_')[-1],u.MaterialSamplerType.SAMPLERTYPE_COLOR))
            link(uv,'',n,'UVs');return n
        loaded={}
        for suffix in ['Color','NormalDX','ARH']:
            name='T_Chapel'+slot+'_'+suffix
            # A material-only rebuild reuses the registered, correctly configured scan.
            if os.environ.get('CHAPEL_RESUME')=='1' and E.does_asset_exist(dest+'/'+name) and slot not in os.environ.get('CHAPEL_REIMPORT_SCANS','').split():
                loaded[suffix]=get(dest+'/'+name)
                continue
            task=u.AssetImportTask();task.filename=str(source/(slot+'_'+suffix+'.png'));task.destination_path=dest
            task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
            A.import_asset_tasks([task])
            tex=get(dest+'/'+name);tex.srgb=(suffix=='Color')
            if suffix=='NormalDX':
                tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP
                tex.flip_green_channel=False
            elif suffix=='ARH':tex.compression_settings=u.TextureCompressionSettings.TC_MASKS
            tex.max_texture_size=2048;save(tex);loaded[suffix]=tex
        uv=node('TextureCoordinate')
        base_height=sample(loaded['ARH'],uv)
        pos=node('WorldPosition'); camera=node('CameraPositionWS')
        dist=node('Distance');link(camera,'',dist,'A');link(pos,'',dist,'B')
        fade=node('OneMinus');link(smooth(200,950,dist),'',fade,'')
        bump=node('BumpOffset')
        link(uv,'',bump,'Coordinate');link(base_height,'B',bump,'Height')
        # Reflected pin names vary between editor releases. Resolve the third pin from the actual expression.
        ratio_pin=L.get_material_expression_input_names(bump)[2]
        link(times(param('NearHeightRatio',ratio),fade),'',bump,str(ratio_pin))
        color=sample(loaded['Color'],bump);normal=sample(loaded['NormalDX'],bump);packed=sample(loaded['ARH'],bump)
        tone=node('VectorParameter')
        tone.set_editor_property('parameter_name','SurfaceTint')
        tone.set_editor_property('default_value',u.LinearColor(*tint,1.))
        # World-scale patina breaks repetition across neighboring assembled modules.
        macro=node('Noise')
        for key,value in [('scale',.0048),('levels',3),('output_min',.87),('output_max',1.04)]:
            macro.set_editor_property(key,value)
        link(pos,'',macro,'')
        shaded=times(times(color,tone),macro)
        rough=(packed,'G')
        if slot=='Flagstone':
            shaded,normal,rough,_=patina['finish_surface'](mat,slot,ground,shaded,normal,rough,(packed,'R'))
        out(shaded,'','BASE_COLOR')
        out(normal,'','NORMAL');out(packed,'R','AMBIENT_OCCLUSION')
        rough_expr,rough_pin=rough if isinstance(rough,tuple) else (rough,'')
        out(rough_expr,rough_pin,'ROUGHNESS')
        L.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
        L.recompile_material(mat);save(mat);result[slot]=mat
        u.log('CHAPEL_RELIEF_MATERIAL '+mat.get_path_name())
    return result

