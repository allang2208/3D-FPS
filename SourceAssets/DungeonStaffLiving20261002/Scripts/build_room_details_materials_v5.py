"""Reuse the accepted shallow-pile PBR graph for green baize, plus new finishes."""
import unreal as u

def build_materials(root,base):
    E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();made=[]
    master=base+'/Materials/M_Staff_BaizeRelief_V5';mat=u.load_asset(master)
    if not mat:
        source=u.load_asset('/Game/Dungeons/StaffLiving20261002/RefinementV3/Materials/M_Staff_NavyCarpet_V3')
        if not source:raise RuntimeError('Missing accepted carpet PBR graph')
        mat=A.duplicate_asset(master.rsplit('/',1)[1],base+'/Materials',source)
        errors=M.recompile_material(mat)
        if errors:raise RuntimeError('Baize material build failed '+str(errors))
        M.get_statistics(mat)
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Baize master save failed')
    path=base+'/Materials/MI_Staff_BaizeRelief_V5';mi=u.load_asset(path)
    if not mi:
        mi=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        M.set_material_instance_parent(mi,mat)
        for name,value in dict(PileTileCm=32.,PileReliefDepthCm=.065,PileNormalStrength=.52,FineNormalStrength=.55,PileFuzzAmount=.18).items():
            M.set_material_instance_scalar_parameter_value(mi,name,value)
        M.set_material_instance_vector_parameter_value(mi,'NavyPileColor',u.LinearColor(.025,.18,.075,1))
        M.update_material_instance(mi)
        if not E.save_loaded_asset(mi,False):raise RuntimeError('Baize instance save failed')
    made.extend((master,path))
    colors=dict(PaddleRed=((.44,.021,.014),.76),PaddleBlack=((.009,.011,.014),.77),
        FreshPlastic=((.57,.58,.53),.28),Coffee=((.021,.009,.003),.16))
    for key,(color,rough) in colors.items():
        path=base+'/Materials/M_Staff_'+key+'_V5';mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
            mat.set_editor_property('used_with_nanite',True)
            n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-240,0)
            n.set_editor_property('constant',u.LinearColor(*color,1));M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
            n=M.create_material_expression(mat,u.MaterialExpressionConstant,-240,100);n.set_editor_property('r',rough)
            M.connect_material_property(n,'',u.MaterialProperty.MP_ROUGHNESS)
            if key.startswith('Paddle'):
                uv=M.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,-600,300)
                n=M.create_material_expression(mat,u.MaterialExpressionCustom,-320,300)
                inp=u.CustomInput();inp.set_editor_property('input_name','UV');n.set_editor_property('inputs',[inp])
                n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
                n.set_editor_property('code','float2 g=sin(UV*1800);return normalize(float3(g*.09,1));')
                M.connect_material_expressions(uv,'',n,'UV');M.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
            errors=M.recompile_material(mat)
            if errors:raise RuntimeError('Fixture material build failed '+str(errors))
            M.get_statistics(mat)
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Fixture material save failed '+path)
        made.append(path)
    texturepath=base+'/Textures/T_Staff_ToiletSign_V5';tex=u.load_asset(texturepath)
    if not tex:
        task=u.AssetImportTask();task.filename=str(root/'RoomDetailsV5/Authored/toilet-sign.png')
        task.destination_path=base+'/Textures';task.destination_name='T_Staff_ToiletSign_V5';task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=u.load_asset(texturepath)
        if not tex or not E.save_loaded_asset(tex,False):raise RuntimeError('Toilet sign import/save failed')
    path=base+'/Materials/M_Staff_ToiletSign_V5';mat=u.load_asset(path)
    if not mat:
        mat=A.create_asset(path.rsplit('/',1)[1],base+'/Materials',u.Material,u.MaterialFactoryNew())
        n=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-240,0);n.set_editor_property('texture',tex)
        M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
        r=M.create_material_expression(mat,u.MaterialExpressionConstant,-240,120);r.set_editor_property('r',.8)
        M.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=M.recompile_material(mat)
        if errors:raise RuntimeError('Toilet sign material build failed '+str(errors))
        M.get_statistics(mat)
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Toilet sign save failed')
    made.extend((path,texturepath));return made
