import unreal as u

def exposure_compensated(mat, source):
    L=u.MaterialEditingLibrary
    inverse=L.create_material_expression(mat,u.MaterialExpressionEyeAdaptationInverse)
    pin=L.get_material_expression_input_names(inverse)[0]
    if not L.connect_material_expressions(source,'',inverse,pin):
        raise RuntimeError('Cannot connect exposure compensation')
    return inverse


def enhance(mat):
    """Upgrade saved paint too; an existing asset must not skip a visual revision."""
    E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
    edges=[node for node in L.get_material_expressions(mat)
           if isinstance(node,u.MaterialExpressionCustom) and 'LocalPosition-BladePivot' in node.get_editor_property('code')]
    if len(edges)!=1:raise RuntimeError('Expected the authored blade-local edge mask')
    edges[0].set_editor_property('code','return smoothstep(13.2,13.4,length((LocalPosition-BladePivot).yz));')
    blend=L.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
    red=L.get_inputs_for_material_expression(mat,blend)[1]
    if not isinstance(red,u.MaterialExpressionConstant3Vector):raise RuntimeError('Expected the red paint input')
    red.set_editor_property('constant',u.LinearColor(.85,.005,.003,1))
    output=L.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
    compensated=isinstance(output,u.MaterialExpressionEyeAdaptationInverse)
    strength=L.get_inputs_for_material_expression(mat,output)[0] if compensated else output
    amount=[n for n in L.get_inputs_for_material_expression(mat,strength) if isinstance(n,u.MaterialExpressionConstant)]
    if len(amount)!=1:raise RuntimeError('Expected the authored paint emission multiplier')
    amount[0].set_editor_property('r',1.5)
    if not compensated:
        output=exposure_compensated(mat,strength)
        if not L.connect_material_property(output,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Cannot apply paint emission')
    E.set_metadata_tag(mat,'WoodworkingSawHighlightRevision','20261013_RedContrast2')
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Enhanced paint material save failed')


def build_guide():
    E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
    folder='/Game/Building/WoodworkingSawHighlight20261013';E.make_directory(folder)
    mat=E.load_asset(folder+'/M_SawCutGuide') if E.does_asset_exist(folder+'/M_SawCutGuide') else None
    if mat:return mat
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_SawCutGuide',folder,u.Material,u.MaterialFactoryNew())
    if not mat:raise RuntimeError('Cannot create cutting-guide material')
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    color=L.create_material_expression(mat,u.MaterialExpressionVertexColor)
    scale=L.create_material_expression(mat,u.MaterialExpressionConstant);scale.set_editor_property('r',1.25)
    strength=L.create_material_expression(mat,u.MaterialExpressionMultiply)
    if not L.connect_material_expressions(color,'',strength,'A') or not L.connect_material_expressions(scale,'',strength,'B'):
        raise RuntimeError('Cannot connect cutting-guide vertex colour')
    output=exposure_compensated(mat,strength)
    if not L.connect_material_property(output,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Cannot apply cutting-guide emission')
    E.set_metadata_tag(mat,'WoodworkingSawHighlightRevision','20261013_RedContrast2')
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Cutting-guide material save failed')
    return mat


def build(dest):
    E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
    folder=dest+'/Materials';E.make_directory(folder)
    existing=E.load_asset(folder+'/M_SawEdgePaint');instance=E.load_asset(folder+'/MI_SawEdgeMerged')
    if existing and instance:
        enhance(existing);L.update_material_instance(instance)
        if not E.save_loaded_asset(instance,False):raise RuntimeError('Merged paint save failed')
        return {'blade':existing,'merged':instance}
    mat=E.duplicate_asset('/Game/Building/WoodworkingBenchV4/Materials/M_WW_PropsAtlas',folder+'/M_SawEdgePaint')
    if not isinstance(mat,u.Material):raise RuntimeError('Cannot duplicate original steel surface')
    def node(cls):return L.create_material_expression(mat,cls)
    def link(src,pin,dst,name):
        if not L.connect_material_expressions(src,pin,dst,name):raise RuntimeError('Cannot connect '+name)
    def scalar(value):
        n=node(u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
    position=node(u.MaterialExpressionWorldPosition)
    local=node(u.MaterialExpressionTransformPosition)
    local.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    local.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    link(position,'',local,'')
    center=node(u.MaterialExpressionVectorParameter);center.set_editor_property('parameter_name','BladePivotCm');center.set_editor_property('default_value',u.LinearColor(0,0,0,0))
    edge=node(u.MaterialExpressionCustom);edge.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    edge.set_editor_property('code','return smoothstep(14.4,14.6,length((LocalPosition-BladePivot).yz));')
    pins=[]
    for name in ['LocalPosition','BladePivot']:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    edge.set_editor_property('inputs',pins);link(local,'',edge,'LocalPosition');link(center,'',edge,'BladePivot')
    red=node(u.MaterialExpressionConstant3Vector);red.set_editor_property('constant',u.LinearColor(.64,.008,.006,1))
    for prop,paint,fallback in [(u.MaterialProperty.MP_BASE_COLOR,red,None),(u.MaterialProperty.MP_METALLIC,scalar(.12),scalar(.8)),(u.MaterialProperty.MP_ROUGHNESS,scalar(.42),scalar(.4))]:
        previous=L.get_material_property_input_node(mat,prop)
        output=L.get_material_property_input_node_output_name(mat,prop) if previous else ''
        if not previous:previous=fallback
        if not previous:raise RuntimeError('Original base colour is unavailable')
        blend=node(u.MaterialExpressionLinearInterpolate);link(previous,output,blend,'A');link(paint,'',blend,'B');link(edge,'',blend,'Alpha')
        if not L.connect_material_property(blend,'',prop):raise RuntimeError('Paint output is unavailable')
    glow=node(u.MaterialExpressionMultiply);link(red,'',glow,'A');link(edge,'',glow,'B')
    strength=node(u.MaterialExpressionMultiply);link(glow,'',strength,'A');link(scalar(.1),'',strength,'B');L.connect_material_property(strength,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    enhance(mat)
    merged=A.create_asset('MI_SawEdgeMerged',folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(merged,mat);L.set_material_instance_vector_parameter_value(merged,'BladePivotCm',u.LinearColor(86.5,0,88.8,0))
    L.update_material_instance(merged)
    if not E.save_loaded_asset(merged,False):raise RuntimeError('Merged paint save failed')
    return {'blade':mat,'merged':merged}
