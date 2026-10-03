"""Workshop-specific print, screen, glass and restrained coatings; save actual assets."""
import hashlib
import unreal as u

def create(root,base,report):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
    E.make_directory(base+'/Materials');E.make_directory(base+'/Textures')
    source=root/'Authored/T_Workshop_PrintAtlas.png';texpath=base+'/Textures/T_Workshop_PrintAtlas'
    tex=u.load_asset(texpath)
    if not tex:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=base+'/Textures'
        task.destination_name='T_Workshop_PrintAtlas';task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(texpath)
        if not tex:raise RuntimeError('Workshop print texture import failed')
        tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',False)
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        if not E.save_loaded_asset(tex,False):raise RuntimeError('Workshop print texture save failed')
    report['materials']=[]
    def start(key):
        path=base+'/Materials/M_Workshop_'+key;mat=u.load_asset(path)
        if mat:return path,mat,False
        mat=A.create_asset('M_Workshop_'+key,base+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('used_with_nanite',key!='Glass');return path,mat,True
    def scalar(mat,value,prop):
        n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value)
        M.connect_material_property(n,'',prop)
    def vector(mat,value,prop):
        n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        n.set_editor_property('constant',u.LinearColor(*value,1));M.connect_material_property(n,'',prop)
    def save(path,mat,new):
        if new:
            errors=list(M.recompile_material(mat))
            if errors:raise RuntimeError('Workshop material compile failed '+path+' '+str(errors))
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Workshop material save failed '+path)
        report['materials'].append(path)
    for key in ('Print','Screen'):
        path,mat,new=start(key)
        if new:
            n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',tex)
            n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
            scalar(mat,.86 if key=='Print' else .29,u.MaterialProperty.MP_ROUGHNESS)
            if key=='Screen':
                multiplier=M.create_material_expression(mat,u.MaterialExpressionMultiply)
                multiplier.set_editor_property('const_b',.3);M.connect_material_expressions(n,'RGB',multiplier,'A')
                M.connect_material_property(multiplier,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        save(path,mat,new)
    for key,color,metal,rough in [('Plaster',(.38,.395,.35),0.,.83),
        ('OfficePlastic',(.095,.105,.11),0.,.49),('Copper',(.48,.19,.065),.86,.32)]:
        path,mat,new=start(key)
        if new:
            vector(mat,color,u.MaterialProperty.MP_BASE_COLOR)
            scalar(mat,metal,u.MaterialProperty.MP_METALLIC);scalar(mat,rough,u.MaterialProperty.MP_ROUGHNESS)
            uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
            grain=M.create_material_expression(mat,u.MaterialExpressionCustom)
            inp=u.CustomInput();inp.set_editor_property('input_name','UV');grain.set_editor_property('inputs',[inp])
            grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
            grain.set_editor_property('code','float f=1-smoothstep(.025,.16,length(fwidth(UV))*500);float2 g=sin(UV*1700+sin(UV.yx*350));return normalize(float3(g*.026*f,1));')
            M.connect_material_expressions(uv,'',grain,'UV');M.connect_material_property(grain,'',u.MaterialProperty.MP_NORMAL)
        save(path,mat,new)
    path,mat,new=start('Glass')
    if new:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('two_sided',True)
        vector(mat,(.23,.32,.32),u.MaterialProperty.MP_BASE_COLOR)
        scalar(mat,.19,u.MaterialProperty.MP_OPACITY);scalar(mat,.12,u.MaterialProperty.MP_ROUGHNESS)
    save(path,mat,new)
    path,mat,new=start('Lamp')
    if new:
        vector(mat,(.5,.58,.58),u.MaterialProperty.MP_BASE_COLOR)
        vector(mat,(1.1,1.25,1.3),u.MaterialProperty.MP_EMISSIVE_COLOR)
        scalar(mat,.43,u.MaterialProperty.MP_ROUGHNESS)
    save(path,mat,new)
    report['texture']=texpath;report['print_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
