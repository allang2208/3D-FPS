"""Save the soft depth-tested Bagua ground material; no playback or preview."""
from pathlib import Path
import json
import shutil
import unreal as u

OUT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
SAVED = []


def build():
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Exit PIE before authoring the soft ground material')
    for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if str(p.get_name()).startswith(DEST + '/'):
            raise RuntimeError('Preserve unsaved soft ground material edits')
    name = 'M_ZhenmoSoftGround'
    path = DEST + '/' + name
    file = Path(u.Paths.project_dir()) / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = OUT / 'Before' / (name + '.uasset')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
    m = u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('material_domain', u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', False)
    m.set_editor_property('disable_depth_test', False)

    def node(cls, **props):
        n = L.create_material_expression(m, cls)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def link(src, dst, pin, output=''):
        if not L.connect_material_expressions(src, output, dst, pin):
            raise RuntimeError('Ground material connection failed: ' + pin)

    texture = u.load_asset('/Game/Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Textures/T_ZhenmoBaguaField')
    if not texture:
        raise RuntimeError('Missing original Bagua field texture')
    inputs = {
        'Ink': node(u.MaterialExpressionTextureObject, texture=texture,
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE),
        'World': node(u.MaterialExpressionWorldPosition),
        'Center': node(u.MaterialExpressionVectorParameter, parameter_name='FieldCenter', default_value=u.LinearColor(0, 0, 0, 0)),
        'Radius': node(u.MaterialExpressionScalarParameter, parameter_name='FieldRadius', default_value=1500.),
        'Opacity': node(u.MaterialExpressionScalarParameter, parameter_name='FieldOpacity', default_value=0.),
        'T': node(u.MaterialExpressionTime),
        'GroundDepth': node(u.MaterialExpressionSceneDepth),
        'PixelDepth': node(u.MaterialExpressionPixelDepth),
        'ViewDirection': node(u.MaterialExpressionCameraVectorWS),
        'SurfaceNormal': node(u.MaterialExpressionPixelNormalWS)}
    pins = []
    for name in inputs:
        p = u.CustomInput()
        p.set_editor_property('input_name', name)
        pins.append(p)
    opacity = node(u.MaterialExpressionCustom, inputs=pins,
                   code=(OUT / 'ground_opacity.hlsl').read_text(encoding='utf-8'),
                   output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    for key, src in inputs.items():
        link(src, opacity, key)
    coverage = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    gold = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    link(opacity, coverage, '')
    link(opacity, gold, '')
    exposed_gold = node(u.MaterialExpressionEyeAdaptationInverse)
    link(gold, exposed_gold, str(L.get_material_expression_input_names(exposed_gold)[0]))
    L.connect_material_property(coverage, '', u.MaterialProperty.MP_OPACITY)
    L.connect_material_property(exposed_gold, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    surface = node(u.MaterialExpressionSubstrateShadingModels, shading_model_override=u.MaterialShadingModel.MSM_UNLIT)
    link(exposed_gold, surface, 'Emissive Color')
    link(coverage, surface, 'Opacity')
    if not L.connect_material_property(surface, '', u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Ground Substrate output failed')
    errors = L.recompile_material(m)
    if errors:
        raise RuntimeError('Soft ground material compilation: ' + str(errors))
    E.set_metadata_tag(m, 'ZhenmoRevision', 'GroundVisibility20261007')
    E.set_metadata_tag(m, 'ZhenmoRendering', 'Depth-tested ground mesh; no projected decal, no monster receiver flags changed')
    if not E.save_loaded_asset(m, False):
        raise RuntimeError('Soft ground material save failed')
    SAVED.append(m.get_path_name())
    receipt = {'complete': True, 'saved_assets': SAVED, 'revision': 'GroundVisibility20261007',
               'edge_fade_radius_fraction': [.86, .995], 'mask_texture_samples': 6,
               'main_seal_radius_cm': 500, 'ground_blend': 'translucent',
               'fade_in_seconds': .65, 'fade_out_seconds': 1.2,
               'character_projection': False, 'runtime_tested': False}
    (OUT / 'asset_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('ZHENMO_SOFT_GROUND_SAVED ' + json.dumps(receipt), flush=True)


if __name__ == '__main__':
    build()
