"""Current PKM finish recipe, shared by authoring and legacy material rebuilds.

Only operates on PKM-private materials and their existing coating nodes.
Call before the importer's normal material compilation/save operation.
"""
from pathlib import Path
import unreal as u
O=Path(__file__).parent
P='/Game/Weapons/PKMLowpoly20260922'
E=u.EditorAssetLibrary; L=u.MaterialEditingLibrary
TEXTURE=P+'/RefinedFinish20260927/Textures/T_PKM_SatinFinish'
REFERENCE='/Game/Weapons/SVDDragunov20260922/RefinedFinish20260923/Textures/T_SVD_SatinFinish'
LABELS={'detail':'PKM20 physical micro finish','color':'PKM20 restrained scuffs',
        'rough':'PKM20 varied roughness','metal':'PKM20 fine exposed metal'}

def profile(path,category=''):
    name=path.rsplit('/',1)[-1].lower()
    if 'titaniumtrim' in name:
        return None
    if 'ammoboxpaint' in name:
        return {'kind':'paint','center':.43,'strength':.22,'tint':[.047,.065,.025],'color_weight':0.}
    if category!='metal' and 'm_pkm23_mount_' not in name:
        return None
    center=.37
    if 'beltlinksteel' in name: center=.33
    elif 'qbz_steel' in name: center=.40
    elif 'interface' in name or 'm_pkm23_mount_' in name: center=.36
    elif any(t in name for t in ['suppressor','brake']): center=.40
    elif 'pkm14_' in name: center=.38
    return {'kind':'metal','center':center,'strength':.26,
            'tint':[.025,.030,.036],'color_weight':.30}

def texture():
    tex=u.load_asset(TEXTURE) if E.does_asset_exist(TEXTURE) else E.duplicate_asset(REFERENCE,TEXTURE)
    if not tex: raise RuntimeError('Cannot create PKM satin grain texture')
    if E.get_metadata_tag(tex,'PKMRefinedFinish')!='20260927':
        tex.set_editor_property('srgb',False)
        tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
        E.set_metadata_tag(tex,'PKMRefinedFinish','20260927')
        E.set_metadata_tag(tex,'WeaponFinishReference',REFERENCE)
        if not E.save_loaded_asset(tex,False): raise RuntimeError('Cannot save PKM satin grain texture')
    return tex

def parameter(mat,cls,name,value):
    obj=next((n for n in L.get_material_expressions(mat) if isinstance(n,cls)
              and str(n.get_editor_property('parameter_name'))==name),None)
    if obj is None:
        obj=L.create_material_expression(mat,cls)
        obj.set_editor_property('parameter_name',name)
    prop='texture' if cls==u.MaterialExpressionTextureObjectParameter else 'default_value'
    obj.set_editor_property(prop,value)
    return obj

def add_input(node,name,source):
    pins=list(node.get_editor_property('inputs'))
    if name not in [str(p.get_editor_property('input_name')) for p in pins]:
        pin=u.CustomInput(); pin.set_editor_property('input_name',name); pins.append(pin)
        node.set_editor_property('inputs',pins)
    if not L.connect_material_expressions(source,'',node,name):
        raise RuntimeError('Cannot connect PKM finish input '+name)

def apply_material(mat,settings=None,finish_texture=None):
    if not isinstance(mat,u.Material) or not mat.get_path_name().startswith(P+'/'):
        return None
    settings=settings or profile(mat.get_path_name(),str(E.get_metadata_tag(mat,'PKM20_Category')))
    if settings is None:return None
    nodes={str(n.get_editor_property('description')):n for n in L.get_material_expressions(mat)
           if isinstance(n,u.MaterialExpressionCustom)}
    for label in LABELS.values():
        if label not in nodes:raise RuntimeError('Missing PKM finish node '+label+' in '+mat.get_path_name())
    tex=finish_texture or texture()
    helper=(O.parent/'PKMLowpoly20260922/Finish20/MicroFinish.hlsl').read_text(encoding='utf-8-sig').split('FinishNoise f;')[0]
    grain=(O/'SatinDetail.hlsl').read_text(encoding='utf-8-sig').replace('__SCRATCH_HELPER__',helper)
    detail=nodes[LABELS['detail']]; detail.set_editor_property('code',grain)
    add_input(detail,'FinishTex',parameter(mat,u.MaterialExpressionTextureObjectParameter,'PKM_SatinFinishTexture',tex))
    center=parameter(mat,u.MaterialExpressionScalarParameter,'PKM_SatinRoughness',settings['center'])
    parameter(mat,u.MaterialExpressionScalarParameter,'PKM_MicroScratchStrength',settings['strength'])
    rough=nodes[LABELS['rough']]; add_input(rough,'Center',center)
    is_paint=settings['kind']=='paint'
    rough.set_editor_property('code',(O/('BoxRoughness.hlsl' if is_paint else 'SteelRoughness.hlsl')).read_text(encoding='utf-8-sig'))
    color=nodes[LABELS['color']]
    color.set_editor_property('code',(O/('BoxColor.hlsl' if is_paint else 'SteelColor.hlsl')).read_text(encoding='utf-8-sig'))
    if is_paint:
        nodes[LABELS['metal']].set_editor_property('code',(O/'BoxMetallic.hlsl').read_text(encoding='utf-8-sig'))
    else:
        tint=parameter(mat,u.MaterialExpressionVectorParameter,'PKM_SatinTint',u.LinearColor(*settings['tint'],1))
        weight=parameter(mat,u.MaterialExpressionScalarParameter,'PKM_SatinColorWeight',settings['color_weight'])
        add_input(color,'Tint',tint); add_input(color,'ColorWeight',weight)
    E.set_metadata_tag(mat,'PKMRefinedFinish','20260927')
    E.set_metadata_tag(mat,'WeaponFinishReference','SVD refined satin grain; QBZ191 metal coating; PKM-specific roughness and olive enamel')
    E.set_metadata_tag(mat,'PKMFinishProfile',str(settings))
    E.set_metadata_tag(mat,'PKMFinishPreserved','UV0 structural normal/AO, metallic/optical regions, weather layer and existing bindings')
    return settings
