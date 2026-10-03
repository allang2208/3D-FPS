"""Create clean espresso-machine powder coat and glazed cup finishes."""
import unreal as u

def build_materials(root,base):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary;made=[]
    E.make_directory(base+'/Materials')
    for key,color,roughness,metallic,glow in [
        ('MachineCoat',(.044,.052,.058),.38,.35,0),
        ('CupGlaze',(.80,.76,.65),.20,0.,0),
        ('Crema',(.24,.10,.030),.26,0.,0),
        ('StatusLight',(.065,.38,.20),.35,0.,.8)]:
        path=base+'/Materials/M_Staff_'+key+'_V7';mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('used_with_nanite',True)
            c=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-450,0)
            c.set_editor_property('constant',u.LinearColor(*color,1))
            M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
            for value,prop,yy in ((roughness,u.MaterialProperty.MP_ROUGHNESS,160),(metallic,u.MaterialProperty.MP_METALLIC,240)):
                n=M.create_material_expression(mat,u.MaterialExpressionConstant,-450,yy)
                n.set_editor_property('r',value);M.connect_material_property(n,'',prop)
            if key=='MachineCoat':
                uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-750,400)
                grain=M.create_material_expression(mat,u.MaterialExpressionCustom,-450,400)
                inp=u.CustomInput();inp.set_editor_property('input_name','UV');grain.set_editor_property('inputs',[inp])
                grain.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
                grain.set_editor_property('code','float fade=1-smoothstep(.04,.25,length(fwidth(UV))*700);float2 g=sin(UV*2900+sin(UV.yx*1300));return normalize(float3(g*.013*fade,1));')
                M.connect_material_expressions(uv,'',grain,'UV');M.connect_material_property(grain,'',u.MaterialProperty.MP_NORMAL)
            if glow:
                n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-450,320)
                n.set_editor_property('constant',u.LinearColor(*(v*glow for v in color),1))
                M.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            errors=list(M.recompile_material(mat))
            if errors:raise RuntimeError('Coffee finish compile failed '+str(errors))
            M.get_statistics(mat)
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Coffee material save failed '+path)
        made.append(path)
    return made
