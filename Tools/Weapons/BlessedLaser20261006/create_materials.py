"""Create and save the blessed laser materials without launching gameplay."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path(__file__).resolve().parents[3]
if Path(u.Paths.project_dir()).resolve() != PROJECT:
    raise RuntimeError('Unexpected project')

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
SOURCE = '/Game/Weapons/ScopeOptics20260927/M_ScopeAwareLaser'
DEST = '/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006'
PREFIX = 'BlessedLaser:'
packages = []
assets = []


def expression(mat, cls, label):
    node = L.create_material_expression(mat, cls)
    node.set_editor_property('desc', PREFIX + ' ' + label)
    return node


def connect(source, target, pin, output=''):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def property_input(node, prop):
    if not L.connect_material_property(node, '', prop):
        raise RuntimeError('Material property connection failed: ' + str(prop))


def primitive_parameter(mat, name, index, default):
    node = expression(mat, u.MaterialExpressionScalarParameter, name)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', default)
    node.set_editor_property('use_custom_primitive_data', True)
    node.set_editor_property('primitive_data_index', index)
    return node


def exposure_emission(mat, source):
    inverse = expression(mat, u.MaterialExpressionEyeAdaptationInverse, 'Daylight exposure compensation')
    light_pin = next(name for name in L.get_material_expression_input_names(inverse) if 'LightValue' in name)
    connect(source, inverse, light_pin)
    property_input(inverse, u.MaterialProperty.MP_EMISSIVE_COLOR)


for kind in ['Dot', 'Beam']:
    path = DEST + '/M_BlessedLaser' + kind
    mat = E.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(SOURCE + kind, path)
    if mat is None:
        raise RuntimeError('Could not create laser material: ' + path)

    # Reauthor only this feature's nodes. Preserve accepted temporal/depth graphs.
    for node in L.get_material_expressions(mat):
        if str(node.get_editor_property('desc')).startswith(PREFIX):
            L.delete_material_expression(mat, node)

    scope = primitive_parameter(mat, 'ScopeAlpha', 0, 0.0)
    time = expression(mat, u.MaterialExpressionTime, 'GPU flow time')
    inputs = {'ScopeAlpha': scope, 'FlowTime': time}
    if kind == 'Beam':
        world = expression(mat, u.MaterialExpressionWorldPosition, 'World position')
        local = expression(mat, u.MaterialExpressionTransformPosition, 'Beam local position')
        local.set_editor_property('transform_source_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        local.set_editor_property('transform_type', u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        connect(world, local, '')
        inputs['LocalPosition'] = local
        inputs['BeamLengthCM'] = primitive_parameter(mat, 'BeamLengthCM', 1, 8000.0)

    effect = expression(mat, u.MaterialExpressionCustom, kind + ' gold emission')
    effect.set_editor_property('code', (Path(__file__).parent / ('blessed_laser_' + kind.lower() + '.hlsl')).read_text(encoding='utf-8'))
    effect.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT4 if kind == 'Beam' else u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    effect.set_editor_property('inputs', pins)
    for name, node in inputs.items():
        connect(node, effect, name)

    if kind == 'Dot':
        exposure_emission(mat, effect)
    else:
        rgb = expression(mat, u.MaterialExpressionComponentMask, 'Gold RGB')
        alpha = expression(mat, u.MaterialExpressionComponentMask, 'Silk opacity')
        for node, channels in [(rgb, 'rgb'), (alpha, 'a')]:
            for channel in 'rgba':
                node.set_editor_property(channel, channel in channels)
            connect(effect, node, '')
        exposure_emission(mat, rgb)
        property_input(alpha, u.MaterialProperty.MP_OPACITY)

    E.set_metadata_tag(mat, 'BlessedLaserVersion', 'gold-silk-v2-exposure')
    E.set_metadata_tag(mat, 'BlessedLaserSource', SOURCE + kind)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Laser material compilation failed: ' + str(errors))
    L.get_statistics(mat)  # Finish shader compilation required for the saved asset.
    packages.append(mat.get_outermost())
    assets.append(path)

saved = u.EditorLoadingAndSavingUtils.save_packages(packages, False)
if not saved:
    raise RuntimeError('Blessed laser material packages did not save')
receipt = {'assets': assets, 'saved': bool(saved), 'source_assets_modified': False,
           'material_recompile_requested': True, 'game_tested': False, 'rendered': False}
out = PROJECT / 'Saved/BlessedLaser20261006'
out.mkdir(parents=True, exist_ok=True)
(out / 'material-save.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('BLESSED_LASER_MATERIALS_SAVED ' + json.dumps(receipt, ensure_ascii=False))
