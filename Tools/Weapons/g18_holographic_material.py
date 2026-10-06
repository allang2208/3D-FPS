"""G18's opaque housing finish with the donor optic's UV0 aperture mask."""
import unreal as u

ROOT = '/Game/Weapons/G18/Integrated20260929'
BODY_PATH = ROOT + '/Materials/M_G18_HoloBodyMasked'
RETICLE_PATH = '/Game/Weapons/M4Holographic/M_HoloReticle'


def ensure_holo_body(save):
    library = u.MaterialEditingLibrary
    donor = u.load_asset('/Game/Weapons/M4Holographic/M_HoloBody')
    finish = u.load_asset(ROOT + '/Materials/M_G18_AttachmentFinish')
    if not donor or not finish:
        raise RuntimeError('Missing G18 finish or holographic aperture source')
    source_mask = library.get_material_property_input_node(donor, u.MaterialProperty.MP_OPACITY_MASK)
    source_output = library.get_material_property_input_node_output_name(donor, u.MaterialProperty.MP_OPACITY_MASK)
    if not isinstance(source_mask, u.MaterialExpressionTextureSample) or source_output != 'A':
        raise RuntimeError('Holographic donor aperture is no longer a texture alpha mask')

    material = u.load_asset(BODY_PATH) if u.EditorAssetLibrary.does_asset_exist(BODY_PATH) else None
    if not material:
        material = u.AssetToolsHelpers.get_asset_tools().duplicate_asset(
            'M_G18_HoloBodyMasked', ROOT + '/Materials', finish)
    if not material:
        raise RuntimeError('Cannot create G18 holographic housing material')
    # Keep the existing G18 steel and WeaponWetness graph. The original lens
    # faces share the housing slot, so replacing this slot with opaque steel
    # also fills the optical opening. Its original UV0 alpha must survive.
    mask = library.get_material_property_input_node(material, u.MaterialProperty.MP_OPACITY_MASK)
    if mask is None:
        mask = library.create_material_expression(material, u.MaterialExpressionTextureSample, -450, 500)
    if not isinstance(mask, u.MaterialExpressionTextureSample):
        raise RuntimeError('Unexpected G18 aperture input; preserve the existing material')
    mask.set_editor_property('texture', source_mask.get_editor_property('texture'))
    mask.set_editor_property('const_coordinate', source_mask.get_editor_property('const_coordinate'))
    mask.set_editor_property('sampler_type', source_mask.get_editor_property('sampler_type'))
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
    material.set_editor_property('opacity_mask_clip_value', donor.get_editor_property('opacity_mask_clip_value'))
    material.set_editor_property('used_with_skeletal_mesh', False)
    if not library.connect_material_property(mask, 'A', u.MaterialProperty.MP_OPACITY_MASK):
        raise RuntimeError('Cannot connect G18 holographic aperture alpha')
    u.EditorAssetLibrary.set_metadata_tag(material, 'G18OpticApertureSource', donor.get_path_name())
    library.recompile_material(material)
    save(material)
    return material


def register_wet_material(material, save):
    assets = u.load_asset(ROOT + '/DA_G18_WetMaterials')
    if not assets:
        raise RuntimeError('Missing G18 weather material catalog')
    wet = dict(assets.get_editor_property('wet_materials'))
    # Point weather back to the masked finish, never the opaque housing donor.
    wet[material.get_path_name()] = material
    assets.set_editor_property('wet_materials', wet)
    save(assets)
