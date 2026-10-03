"""Compile the owned V6 text finishes and clean kettle surface materials."""
import unreal as u
def build_materials(root,base):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary;made=[]
    E.make_directory(base+'/Textures');E.make_directory(base+'/Materials')
    def save(a):
        if not a or not E.save_loaded_asset(a,False):raise RuntimeError('V6 material production save failed')
        made.append(a.get_path_name().split('.')[0])
    for key in ('Labels','Notices'):
        path=base+'/Textures/T_Staff_'+key+'_V6';tex=u.load_asset(path)
        if not tex:
            task=u.AssetImportTask();task.filename=str(root/('WallInsetV6/Authored/T_Staff_'+key+'_V6.png'))
            task.destination_path=base+'/Textures';task.destination_name=path.rsplit('/',1)[1]
            task.automated=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(path)
            if not tex:raise RuntimeError('V6 font atlas import failed')
            tex.set_editor_property('srgb',True);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
            tex.set_editor_property('max_texture_size',4096);tex.set_editor_property('never_stream',False)
            tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
            save(tex)
        else:made.append(path)
        path=base+'/Materials/M_Staff_'+key+'_V6';mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('used_with_nanite',True);mat.set_editor_property('used_with_instanced_static_meshes',True)
            slab=M.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
            slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
            texnode=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-360,0);texnode.set_editor_property('texture',tex)
            texnode.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            rough=M.create_material_expression(mat,u.MaterialExpressionConstant,-360,160);rough.set_editor_property('r',.82)
            M.connect_material_expressions(texnode,'RGB',slab,'BaseColor');M.connect_material_expressions(rough,'',slab,'Roughness')
            M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
            errors=list(M.recompile_material(mat))
            if errors:raise RuntimeError('V6 typography material compile failed '+str(errors))
            M.get_statistics(mat);save(mat)
        else:made.append(path)
    for key,color,roughness,metallic in [('Stainless',(.56,.58,.60),.27,1.),('KettleRubber',(.014,.017,.020),.56,0.)]:
        path=base+'/Materials/M_Staff_'+key+'_V6';mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('used_with_nanite',True)
            c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-450,0);c.set_editor_property('constant',u.LinearColor(*color,1))
            M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
            for value,prop,yy in ((roughness,u.MaterialProperty.MP_ROUGHNESS,160),(metallic,u.MaterialProperty.MP_METALLIC,240)):
                c=M.create_material_expression(mat,u.MaterialExpressionConstant,-450,yy);c.set_editor_property('r',value);M.connect_material_property(c,'',prop)
            uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-750,400)
            n=M.create_material_expression(mat,u.MaterialExpressionCustom,-450,400)
            inp=u.CustomInput();inp.set_editor_property('input_name','UV');n.set_editor_property('inputs',[inp])
            n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
            n.set_editor_property('code','float fade=1-smoothstep(.08,.3,length(fwidth(UV))*1800);float grain=sin(UV.y*6500);return normalize(float3(0,grain*.035*fade,1));' if key=='Stainless' else
                'float2 g=sin(UV*2100);float fade=1-smoothstep(.05,.3,length(fwidth(UV))*600);return normalize(float3(g*.018*fade,1));')
            M.connect_material_expressions(uv,'',n,'UV');M.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
            errors=list(M.recompile_material(mat))
            if errors:raise RuntimeError('Kettle surface material compile failed '+str(errors))
            M.get_statistics(mat);save(mat)
        else:made.append(path)
    return made
