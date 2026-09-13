"""Build only the resolved-color UI material; keep the existing workbench assets."""
import unreal

DEST = '/Game/UI/GunsmithWorkbench'
NAME = 'M_WeaponPreviewResolved'
lib = unreal.MaterialEditingLibrary
material = unreal.load_asset(f'{DEST}/{NAME}')
if material is None:
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        NAME, DEST, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(material)
material.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
default = unreal.load_asset(f'{DEST}/RT_PreviewDefault')
if default is None:
    raise RuntimeError('Existing workbench render-target default is missing')
for parameter, channel, output in (
    ('PreviewTexture', 'RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR),
    ('PreviewCoverage', 'A', unreal.MaterialProperty.MP_OPACITY),
):
    sample = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name', parameter)
    sample.texture = default
    sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    if parameter == 'PreviewCoverage':
        inverse = lib.create_material_expression(material, unreal.MaterialExpressionOneMinus)
        lib.connect_material_expressions(sample, channel, inverse, '')
        lib.connect_material_property(inverse, '', output)
    else:
        lib.connect_material_property(sample, channel, output)
lib.recompile_material(material)
if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
    raise RuntimeError('Could not save resolved preview material')
unreal.log('GUNSMITH_PREVIEW_RESOLVED_MATERIAL_SAVED')
