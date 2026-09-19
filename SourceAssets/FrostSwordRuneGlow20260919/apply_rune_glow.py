"""Upgrade the live blade-rune material without replacing the graph or mesh.

Execute in the FPSGAME editor with Tools/AssetPipeline/ue_python_exec.py.
Only this material is saved; no map, game session, or visual test is started.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

import unreal as ue

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
ASSET = '/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2'
REVISION = 'FrostRuneGlow20260919'
L = ue.MaterialEditingLibrary
material = ue.load_asset(ASSET)
if material is None:
    raise RuntimeError('The installed blade-rune material is missing: ' + ASSET)

nodes = list(L.get_material_expressions(material))
custom = next(n for n in nodes if isinstance(n, ue.MaterialExpressionCustom)
              and 'RuneTexture' in str(n.get_editor_property('code')))
backup = ROOT / 'Before'
backup.mkdir(exist_ok=True)
original = PROJECT / 'Content' / (ASSET.removeprefix('/Game/') + '.uasset')
if not (backup / original.name).exists():
    shutil.copy2(original, backup / original.name)
    (backup / 'silver_runes.hlsl').write_text(custom.get_editor_property('code'), encoding='utf-8')


def node(cls, label, **properties):
    expression = next((n for n in nodes if isinstance(n, cls)
                       and n.get_editor_property('desc') == REVISION + ':' + label), None)
    if expression is None:
        expression = L.create_material_expression(material, cls)
        expression.set_editor_property('desc', REVISION + ':' + label)
        nodes.append(expression)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression


def parameter(cls, name, value):
    expression = next((n for n in nodes if isinstance(n, cls)
                       and str(n.get_editor_property('parameter_name')) == name), None)
    if expression is None:
        expression = node(cls, name, parameter_name=name)
    expression.set_editor_property('default_value', value)
    expression.set_editor_property('group', 'Rune appearance')
    return expression


def connect(source, output, target, input_name):
    if not L.connect_material_expressions(source, output, target, input_name):
        raise RuntimeError('Cannot connect rune material input: ' + input_name)


colors = {'RuneBaseColor': (.82, .89, 1.0, 1.0),
          'RuneGlowColor': (.55, .78, 1.0, 1.0)}
scalars = {'BaseBrightness': 1.35, 'GlowStrength': 2.8, 'RuneOpacity': .96,
           'HaloOpacity': .20, 'HaloRadiusTexels': 2.5}
inputs = list(custom.get_editor_property('inputs'))
names = {str(pin.get_editor_property('input_name')) for pin in inputs}
for name in (*colors, *scalars):
    if name not in names:
        pin = ue.CustomInput()
        pin.set_editor_property('input_name', name)
        inputs.append(pin)
custom.set_editor_property('inputs', inputs)
custom.set_editor_property('code', (ROOT / 'silver_runes.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description', 'Pearl-silver rune core and soft ice-blue fluorescence')
for name, value in colors.items():
    connect(parameter(ue.MaterialExpressionVectorParameter, name, ue.LinearColor(*value)),
            'RGB', custom, name)
for name, value in scalars.items():
    connect(parameter(ue.MaterialExpressionScalarParameter, name, value), '', custom, name)

rgb = node(ue.MaterialExpressionComponentMask, 'FluorescenceRGB', r=True, g=True, b=True, a=False)
alpha = node(ue.MaterialExpressionComponentMask, 'Coverage', r=False, g=False, b=False, a=True)
connect(custom, '', rgb, str(L.get_material_expression_input_names(rgb)[0]))
connect(custom, '', alpha, str(L.get_material_expression_input_names(alpha)[0]))

# The old unlit overlay used fixed world luminance. Compensate the exposure
# locally so lighting changes cannot turn an opaque rune core into a dark mark.
exposure = node(ue.MaterialExpressionEyeAdaptationInverse, 'ExposureCompensatedGlow')
exposure_inputs = list(L.get_material_expression_input_names(exposure))
connect(rgb, '', exposure, str(exposure_inputs[0]))
connect(parameter(ue.MaterialExpressionScalarParameter, 'ExposureCompensation', 1.0),
        '', exposure, str(exposure_inputs[1]))
if not L.connect_material_property(exposure, '', ue.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Cannot connect rune emissive output')
if not L.connect_material_property(alpha, '', ue.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Cannot connect rune coverage output')
material.set_editor_property('blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('enable_responsive_aa', True)
# The installed material already carries its skeletal-mesh usage flag.
L.layout_material_expressions(material)
errors = list(L.recompile_material(material))
if errors:
    raise RuntimeError('Rune shader compilation failed: ' + '\n'.join(errors))
ue.EditorAssetLibrary.set_metadata_tag(material, 'RuneAppearanceRevision', REVISION)
ue.EditorAssetLibrary.set_metadata_tag(material, 'RuneAppearance',
    'Pearl-silver core, ice-blue emissive halo, gentle nonzero pulse, local exposure compensation')
if not ue.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Failed to save rune material')
(ROOT / 'install_receipt.json').write_text(json.dumps({
    'installed_at': datetime.now().isoformat(timespec='seconds'),
    'material': material.get_path_name(), 'colors_linear': colors, 'scalars': scalars,
    'exposure_compensation': 1.0, 'shader_compile_errors': errors,
    'runtime_testing': 'not run; user will test',
}, ensure_ascii=False, indent=2), encoding='utf-8')
ue.log('FROST_RUNE_GLOW_INSTALLED ' + material.get_path_name())
