"""Keep Chixiao's native red inlay and brass rails outside blade finishes."""
import unreal as u

L = u.MaterialEditingLibrary
REVISION = 'ChixiaoInlayPreservation20261110V1'
SURFACE_NAME = 'M_TangDaoBladeRuneSurface_Zhanmadao_chixiao_V1'
FINISH_PREFIX = 'SharedTwoHandFinish20261101V1 '
MASK_CODE = '''// The authored steel is neutral/cool; only the red inlay and brass rails
// have positive red chroma. Reuse the original UV0 base-color sample, including
// its mip filtering, so the protection follows both faces and their fade ends.
// Shared finish recipes interpret Mask * 3 as the protected coverage.
float chroma=NativeColor.r-max(NativeColor.g,NativeColor.b);
return smoothstep(.002,.020,chroma)/3.0;
'''
DETAIL_CODES = {
    'ANISOTROPY': 'if(Mode>4.5&&Mode<5.5)return lerp(Base,(.20+.07*Crystal.a)*(1-.7*Edge),1-saturate(Mask*3.0));return Base;',
    'TANGENT': 'if(Mode>4.5&&Mode<5.5)return normalize(lerp(Base,Brush,1-saturate(Mask*3.0)));return Base;',
}


def apply_surface_protection(material, texture_name, revision, code,
                             input_name='NativeColor', channel='RGB',
                             metadata='ChixiaoInlayRevision'):
    nodes = list(L.get_material_expressions(material))
    fields = {str(n.get_editor_property('desc'))[len(FINISH_PREFIX):]: n for n in nodes
              if isinstance(n, u.MaterialExpressionCustom)
              and str(n.get_editor_property('desc')).startswith(FINISH_PREFIX)}
    if not fields:
        # No-finish/temporal surfaces already retain their native PBR.
        return False
    channels = ('BASE_COLOR', 'ROUGHNESS', 'NORMAL', 'METALLIC', 'ANISOTROPY', 'TANGENT')
    if any(field not in fields for field in channels):
        raise RuntimeError('Incomplete blade finish graph: ' + material.get_path_name())
    native = next((n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample)
                   and n.get_editor_property('texture')
                   and n.get_editor_property('texture').get_name() == texture_name), None)
    if native is None:
        raise RuntimeError('Missing native blade sample ' + texture_name)
    mask = next((n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                 and str(n.get_editor_property('desc')) == revision), None)
    if mask is None:
        mask = L.create_material_expression(material, u.MaterialExpressionCustom)
    # A newly authored blade may inherit the donor's mask node while replacing
    # its texture atlas. Retarget the input contract as well as the shader code.
    if [str(pin.get_editor_property('input_name')) for pin in mask.get_editor_property('inputs')] != [input_name]:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', input_name)
        mask.set_editor_property('inputs', [pin])
    mask.set_editor_properties(dict(desc=revision, code=code,
                                   output_type=u.CustomMaterialOutputType.CMOT_FLOAT1))
    if not L.connect_material_expressions(native, channel, mask, input_name):
        raise RuntimeError('Cannot connect native blade sample ' + texture_name)
    for field in channels:
        node = fields[field]
        if field in DETAIL_CODES:
            inputs = list(node.get_editor_property('inputs'))
            if not any(str(pin.get_editor_property('input_name')) == 'Mask' for pin in inputs):
                pin = u.CustomInput()
                pin.set_editor_property('input_name', 'Mask')
                inputs.append(pin)
                node.set_editor_property('inputs', inputs)
            node.set_editor_property('code', DETAIL_CODES[field])
        if not L.connect_material_expressions(mask, '', node, 'Mask'):
            raise RuntimeError('Cannot protect blade ' + field)
    u.EditorAssetLibrary.set_metadata_tag(material, metadata, revision)
    return True


def apply_inlay_protection(material):
    if material.get_name() not in (SURFACE_NAME, SURFACE_NAME + '_Whirlwind'):
        return False
    return apply_surface_protection(material, 'T_Chixiao_BaseColor_V1', REVISION, MASK_CODE)
