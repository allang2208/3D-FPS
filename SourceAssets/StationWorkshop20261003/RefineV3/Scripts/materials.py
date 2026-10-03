"""Smooth, matte concrete with a planar geometric surface."""
import unreal as u
def create(root,base,report):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
    path=base+'/Materials/M_Workshop_FlatConcrete';mat=u.load_asset(path)
    if not mat:
        E.make_directory(base+'/Materials')
        mat=A.create_asset('M_Workshop_FlatConcrete',base+'/Materials',u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('used_with_nanite',True)
        color=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
        color.set_editor_property('constant',u.LinearColor(.27,.28,.26,1))
        M.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
        for value,prop in ((.86,u.MaterialProperty.MP_ROUGHNESS),(.18,u.MaterialProperty.MP_SPECULAR)):
            n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value)
            M.connect_material_property(n,'',prop)
        errors=M.recompile_material(mat)
        if errors:raise RuntimeError('Concrete material compile failed '+str(errors))
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Concrete material save failed')
    report['materials']=[path]
