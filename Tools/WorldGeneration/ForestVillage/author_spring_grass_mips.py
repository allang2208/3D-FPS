"""Author streamable mips on the two original spring grass scans shared by the hills grass materials."""
import unreal as u

FOLDER='/Game/PN_GrassLibrary/Textures/grassTextures/MasterTextures/'
COLOR=FOLDER+'springGrass_Albedo_8k_I'
MASK=FOLDER+'springGrass_Opacity_8k'

def mask_channel(mat,node,output,mask):
    edit=u.MaterialEditingLibrary
    if isinstance(node,u.MaterialExpressionTextureSample) and node.texture==mask:
        return output if output in ('R','G','B','A') else 'R'
    if isinstance(node,u.MaterialExpressionReroute):
        source,=edit.get_inputs_for_material_expression(mat,node)
        pin=edit.get_input_node_output_name_for_material_expression(node,source)
        return mask_channel(mat,source,pin or output,mask)
    if isinstance(node,u.MaterialExpressionMultiply):
        inputs=[v for v in edit.get_inputs_for_material_expression(mat,node) if v]
        for i,source in enumerate(inputs):
            if len(inputs)==2 and isinstance(inputs[1-i],u.MaterialExpressionPerInstanceFadeAmount):
                return mask_channel(mat,source,edit.get_input_node_output_name_for_material_expression(node,source),mask)
    raise RuntimeError(f'Unrecognized spring grass opacity input in {mat.get_path_name()}: {node}')

def install():
    library=u.EditorAssetLibrary
    edit=u.MaterialEditingLibrary
    mask=u.load_asset(MASK)
    color=u.load_asset(COLOR)
    if not isinstance(mask,u.Texture2D) or not isinstance(color,u.Texture2D):
        raise RuntimeError('Spring grass source textures are missing')
    registry=u.AssetRegistryHelpers.get_asset_registry()
    registry.wait_for_completion()
    opts=u.AssetRegistryDependencyOptions(include_hard_package_references=True)
    uses={}
    channels={}
    for path in sorted(str(k) for k in registry.get_referencers(MASK,opts) or []):
        mat=u.load_asset(path)
        if not isinstance(mat,u.Material):continue
        root=edit.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY_MASK)
        output=edit.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_OPACITY_MASK)
        clip=float(mat.get_editor_property('opacity_mask_clip_value'))
        channel=mask_channel(mat,root,output,mask)
        uses[path]=dict(root=root.get_name(),channel=channel,clip=clip)
        if channel in channels and abs(channels[channel]-clip)>.001:
            raise RuntimeError(f'Different {channel} cutouts on shared spring grass: {uses}')
        channels[channel]=clip
    if '/Game/WorldGeneration/TemperateHills/Grass/M_TemperateMeadow' not in uses:
        raise RuntimeError('Missing hills material reference')
    thresholds=u.Vector4(*(channels.get(c,0.) for c in 'RGBA'))
    for tex in (color,mask):
        tex.modify()
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        tex.set_editor_property('never_stream',False)
        if tex==mask:
            tex.set_editor_property('alpha_coverage_thresholds',thresholds)
            tex.set_editor_property('do_scale_mips_for_alpha_coverage',True)
        if not library.save_loaded_asset(tex,False):raise RuntimeError(tex.get_path_name())
    return uses
