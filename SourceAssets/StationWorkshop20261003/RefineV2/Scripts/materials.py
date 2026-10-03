"""Private keycap/legend materials; retain accepted metal, housing and paper surfaces."""
import unreal as u
def create(root,base,report):
    E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
    E.make_directory(base+'/Materials');E.make_directory(base+'/Textures')
    path=base+'/Textures/T_Office_KeyLegends';texture=u.load_asset(path)
    if not texture:
        t=u.AssetImportTask();t.filename=str(root/'Authored/T_Office_KeyLegends.png');t.destination_path=base+'/Textures'
        t.destination_name='T_Office_KeyLegends';t.automated=True;t.save=False;A.import_asset_tasks([t]);texture=u.load_asset(path)
        if not texture:raise RuntimeError('Legend atlas import failed')
        texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
        if not E.save_loaded_asset(texture,False):raise RuntimeError('Legend atlas save failed')
    report['texture']=path;report['materials']=[]
    def constant(mat,value,prop):
        n=M.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',value);M.connect_material_property(n,'',prop)
    for key in ('Keycaps','Legends','Display'):
        path=base+'/Materials/M_Office_'+key;mat=u.load_asset(path)
        if not mat:
            mat=A.create_asset('M_Office_'+key,base+'/Materials',u.Material,u.MaterialFactoryNew());mat.set_editor_property('used_with_nanite',True)
            if key=='Legends':
                n=M.create_material_expression(mat,u.MaterialExpressionTextureSample);n.set_editor_property('texture',texture)
                n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR);M.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
            elif key=='Keycaps':
                n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(.0176,.0176,.0176,1))
                M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
            else:
                n=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(.02,.06,.05,1))
                M.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
                M.connect_material_property(n,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            constant(mat,.52,u.MaterialProperty.MP_ROUGHNESS);constant(mat,.22,u.MaterialProperty.MP_SPECULAR)
            errors=M.recompile_material(mat)
            if errors:raise RuntimeError('Office material compile failed '+str(errors))
            if not E.save_loaded_asset(mat,False):raise RuntimeError('Office material save failed')
        report['materials'].append(path)
