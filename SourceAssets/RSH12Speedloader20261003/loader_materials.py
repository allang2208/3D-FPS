"""Production materials for the carrier and the five retention collars."""
import unreal as u

def create(root,save):
    result={}
    for name,color,roughness,metallic in (
        ('LoaderPolymer',(0.022,0.025,0.028),.46,0.),
        ('LoaderSteel',(.22,.24,.26),.29,1.)):
        asset='M_RSH12_'+name;path=root+'/Materials'
        mat=u.load_asset(path+'/'+asset)
        if not mat:mat=u.AssetToolsHelpers.get_asset_tools().create_asset(asset,path,u.Material,u.MaterialFactoryNew())
        lib=u.MaterialEditingLibrary;lib.delete_all_material_expressions(mat)
        base=lib.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-300,0)
        base.constant=u.LinearColor(*color,1.)
        lib.connect_material_property(base,'',u.MaterialProperty.MP_BASE_COLOR)
        for y,value,prop in ((100,roughness,u.MaterialProperty.MP_ROUGHNESS),(200,metallic,u.MaterialProperty.MP_METALLIC)):
            expr=lib.create_material_expression(mat,u.MaterialExpressionConstant,-300,y);expr.r=value
            lib.connect_material_property(expr,'',prop)
        mat.set_editor_property('used_with_skeletal_mesh',True);lib.recompile_material(mat);save(mat)
        result[name]=mat
    return result
