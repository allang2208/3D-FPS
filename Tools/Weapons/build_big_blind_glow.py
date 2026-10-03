"""Author and save Big Blind's original pulsing gold muzzle material.

Run through UE's background Python commandlet; no preview or runtime tests.
One 8 cm card and one shadowless 32 cm point light per enchanted held pistol.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
DEST = '/Game/Weapons/BigBlind20261002'
NAME = 'M_BigBlindMuzzlePulse'
TAG = 'FPSGAME.BigBlind'
VERSION = 'V1'
A = u.EditorAssetLibrary
L = u.MaterialEditingLibrary


def node(mat, cls, **props):
    result = L.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Material connection failed: ' + str(pin))


def build():
    path = DEST + '/' + NAME
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved material: ' + path)
    mat = u.load_asset(path) if A.does_asset_exist(path) else None
    if mat and A.get_metadata_tag(mat, TAG) != VERSION:
        raise RuntimeError('Preserve unowned material: ' + path)
    if not mat:
        mat = u.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DEST, u.Material, u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Material creation failed: ' + path)
    for expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, expression)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    inputs = {'UV': node(mat, u.MaterialExpressionTextureCoordinate),
              'Exposure': node(mat, u.MaterialExpressionEyeAdaptation),
              'Phase': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Phase', default_value=0.5),
              'Strength': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Strength', default_value=1.0)}
    code = (ROOT / 'SourceAssets/BigBlind20261002/BigBlindMuzzlePulse.hlsl').read_text(encoding='utf-8')
    custom = node(mat, u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    for key, expression in inputs.items():
        wire(expression, custom, key)
    rgb = node(mat, u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(mat, u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(custom, rgb)
    wire(custom, alpha)
    depth = node(mat, u.MaterialExpressionDepthFade, fade_distance_default=1.0)
    wire(alpha, depth, 0)
    L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(depth, '', u.MaterialProperty.MP_OPACITY)
    temporal = node(mat, u.MaterialExpressionTemporalResponsivenessOutput)
    wire(node(mat, u.MaterialExpressionConstant, r=1.0), temporal, 0)
    L.recompile_material(mat)
    A.set_metadata_tag(mat, TAG, VERSION)
    if not A.save_loaded_asset(mat, False):
        raise RuntimeError('Material save failed: ' + path)
    receipt = ROOT / 'Saved/BigBlind/authored.json'
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'version': VERSION, 'saved': [mat.get_path_name()],
                                   'original_analytic_material': True, 'pulse_seconds': 1.4,
                                   'runtime_tested': False, 'rendered': False}, indent=2), encoding='utf-8')
    u.log('BIG_BLIND_AUTHORING_COMPLETE ' + str(receipt))


if __name__ == '__main__':
    build()
